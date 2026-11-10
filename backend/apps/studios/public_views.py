"""Customer-facing studio catalog (``/api/v1/public/studios/…``) and the studio's own portfolio,
calendar and chats (``/api/v1/studios/me/{studio_id}/…``).

Public endpoints show only active studios, their portfolio, rating and *how busy* each day is —
never ceremony titles, customers or staff. Reels, likes / dislikes, comments and chat work only
while the studio's galichka (paid badge) is active (``services.BadgeRequired`` otherwise).
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.access import AccessNote
from apps.ceremonies.permissions import IsClientUser, IsStudioMember
from apps.reviews.models import TargetKind
from apps.reviews.services import stats_map
from apps.venues.scheduling import parse_date, parse_range

from . import chat, services
from .models import (
    MAX_PORTFOLIO_IMAGES,
    MAX_PORTFOLIO_REELS,
    StudioConversation,
    StudioImage,
    StudioMembership,
    StudioPortfolioComment,
)
from .serializers import (
    ChatMessageSerializer,
    ChatMessageWriteSerializer,
    CommentSerializer,
    CommentWriteSerializer,
    DayStatusWriteSerializer,
    EngagementSerializer,
    OffWeekdaysSerializer,
    PortfolioItemSerializer,
    PortfolioItemUpdateSerializer,
    PortfolioUsageSerializer,
    PublicStudioSerializer,
    ReactionWriteSerializer,
    ReelUploadSerializer,
    StudioConversationSerializer,
    StudioImageSerializer,
    StudioImageUploadSerializer,
    StudioPanelScheduleSerializer,
    StudioScheduleSerializer,
    StudioThreadSerializer,
    UserConversationSerializer,
    UserThreadSerializer,
)

UUID_RE = r"[0-9a-fA-F-]{36}"
PUBLIC_ONLY = "Faqat faol studiyalar; xodimlar, mijozlar va marosim nomlari qaytmaydi."
BADGE_ONLY = "Faqat galichkasi faol studiya (aks holda 403 badge_required)."


def _user(request):
    return request.user if request.user.is_authenticated else None


class PublicStudioViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicStudioSerializer
    lookup_value_regex = UUID_RE
    pagination_class = None
    filter_backends = []
    access_notes = {"*": AccessNote(conditions=(PUBLIC_ONLY,))}

    def get_queryset(self):
        return services.public_studios().prefetch_related("images")

    def _context(self, studios, stats=None) -> dict:
        ids = [item.pk for s in studios for item in s.images.all()]
        return {
            "request": self.request,
            "stats": stats,
            "engagement": services.engagement_map(ids, _user(self.request)),
        }

    @extend_schema(
        summary="Studiyalar (ommaviy katalog, reyting bo'yicha)",
        tags=["studios-public"],
        parameters=[OpenApiParameter("q", str, description="Nomi / manzili")],
        responses=PublicStudioSerializer(many=True),
    )
    def list(self, request):
        studios = self.get_queryset()
        q = request.query_params.get("q", "").strip()
        if q:
            studios = studios.filter(Q(name__icontains=q) | Q(address__icontains=q))
        studios = list(studios[:200])
        stats = stats_map(TargetKind.STUDIO, [s.pk for s in studios])
        studios.sort(key=lambda s: (-(stats[s.pk]["rating_avg"] or 0), -stats[s.pk]["like_count"], s.name))
        return Response(self.get_serializer(studios, many=True, context=self._context(studios, stats)).data)

    @extend_schema(summary="Studiya (ommaviy profil, portfolio va reels)", tags=["studios-public"])
    def retrieve(self, request, pk=None):
        studio = self.get_object()
        return Response(PublicStudioSerializer(studio, context=self._context([studio])).data)

    @extend_schema(
        summary="Studiya grafigi: band, dam olish va bo'sh kunlar",
        tags=["studios-public"],
        parameters=[
            OpenApiParameter("from", OpenApiTypes.DATE, required=True),
            OpenApiParameter("to", OpenApiTypes.DATE, required=True, description="Ko'pi bilan 62 kun."),
        ],
        responses=StudioScheduleSerializer,
    )
    @action(detail=True, methods=["get"])
    def schedule(self, request, pk=None):
        studio = self.get_object()
        start, end = parse_range(request.query_params)
        return Response(StudioScheduleSerializer(services.schedule(studio, start, end)).data)


# --------------------------------------------- public portfolio interactions
def _public_item(studio_id, item_id) -> StudioImage:
    studio = get_object_or_404(services.public_studios(), pk=studio_id)
    return get_object_or_404(services.public_items(studio).select_related("studio"), pk=item_id)


class PortfolioReactionView(APIView):
    permission_classes = [IsClientUser]
    access_notes = {"*": AccessNote(ownership="Faqat so'rovchining o'z bahosi.", conditions=(PUBLIC_ONLY, BADGE_ONLY))}

    @extend_schema(
        summary="Portfolio ishiga like / dislike",
        tags=["studios-public"],
        request=ReactionWriteSerializer,
        responses=EngagementSerializer,
    )
    def put(self, request, studio_id, item_id):
        item = _public_item(studio_id, item_id)
        body = ReactionWriteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return Response(services.set_reaction(item, request.user, body.validated_data["value"]))

    @extend_schema(summary="Like / dislike'ni olib tashlash", tags=["studios-public"], responses=EngagementSerializer)
    def delete(self, request, studio_id, item_id):
        return Response(services.set_reaction(_public_item(studio_id, item_id), request.user, None))


class PortfolioCommentsView(APIView):
    access_notes = {
        "get": AccessNote(conditions=(PUBLIC_ONLY, "Yashirilgan izohlar ko'rinmaydi.")),
        "post": AccessNote(conditions=(PUBLIC_ONLY, BADGE_ONLY)),
    }

    def get_permissions(self):
        return [IsClientUser()] if self.request.method == "POST" else [AllowAny()]

    @extend_schema(summary="Portfolio ishining izohlari", tags=["studios-public"], responses=CommentSerializer(many=True))
    def get(self, request, studio_id, item_id):
        item = _public_item(studio_id, item_id)
        comments = services.visible_comments(item)[:200]
        return Response(CommentSerializer(comments, many=True, context={"request": request}).data)

    @extend_schema(
        summary="Izoh yozish",
        tags=["studios-public"],
        request=CommentWriteSerializer,
        responses={201: CommentSerializer},
    )
    def post(self, request, studio_id, item_id):
        item = _public_item(studio_id, item_id)
        body = CommentWriteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        comment = services.add_comment(request, item, body.validated_data["text"])
        return Response(CommentSerializer(comment, context={"request": request}).data, status=status.HTTP_201_CREATED)


class PortfolioMyCommentView(APIView):
    permission_classes = [IsClientUser]
    access_notes = {"*": AccessNote(ownership="Faqat so'rovchining o'z izohi; boshqasi 404.")}

    @extend_schema(summary="O'z izohimni o'chirish", tags=["studios-public"], responses={204: None})
    def delete(self, request, studio_id, item_id, comment_id):
        item = _public_item(studio_id, item_id)
        comment = get_object_or_404(StudioPortfolioComment, pk=comment_id, item=item, author=request.user)
        services.delete_comment(request, comment, by_studio=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------- customer chats
CUSTOMER_CHATS = "Faqat so'rovchining o'z suhbatlari."


class MyStudioChatsView(APIView):
    permission_classes = [IsClientUser]
    access_notes = {"*": AccessNote(ownership=CUSTOMER_CHATS)}

    @extend_schema(summary="Studiyalar bilan suhbatlarim", tags=["studio-chat"], responses=UserConversationSerializer(many=True))
    def get(self, request):
        conversations = list(chat.user_conversations(request.user)[:100])
        context = {"last_messages": chat.last_messages(conversations)}
        return Response(UserConversationSerializer(conversations, many=True, context=context).data)


class MyStudioChatView(APIView):
    permission_classes = [IsClientUser]
    access_notes = {
        "*": AccessNote(ownership=CUSTOMER_CHATS, conditions=(PUBLIC_ONLY,)),
        "post": AccessNote(ownership=CUSTOMER_CHATS, conditions=(PUBLIC_ONLY, BADGE_ONLY)),
    }

    def _studio(self, studio_id):
        return get_object_or_404(services.public_studios(), pk=studio_id)

    @extend_schema(summary="Studiya bilan suhbat (xabarlar)", tags=["studio-chat"], responses=UserThreadSerializer)
    def get(self, request, studio_id):
        studio = self._studio(studio_id)
        conversation = StudioConversation.objects.filter(studio=studio, user=request.user).first()
        messages = []
        if conversation is not None:
            messages = chat.messages(conversation)
            chat.mark_read(conversation, by_studio=False)
        data = {"studio": studio, "can_write": services.has_badge(studio), "messages": messages}
        return Response(UserThreadSerializer(data).data)

    @extend_schema(
        summary="Studiyaga xabar yozish",
        tags=["studio-chat"],
        request=ChatMessageWriteSerializer,
        responses={201: ChatMessageSerializer},
    )
    def post(self, request, studio_id):
        studio = self._studio(studio_id)
        body = ChatMessageWriteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        message = chat.send_from_user(request.user, studio, body.validated_data["body"])
        return Response(ChatMessageSerializer(message).data, status=status.HTTP_201_CREATED)


# ------------------------------------------------------- studio's own side
OWN_STUDIO = "Faqat so'rovchi faol a'zo bo'lgan studiya; o'zgartirish — OWNER yoki MANAGER. Boshqasi 404."


def _membership(request, studio_id):
    membership = get_object_or_404(services.active_memberships(request.user), studio_id=studio_id)
    if request.method not in ("GET", "HEAD", "OPTIONS") and membership.role not in StudioMembership.MANAGING_ROLES:
        raise PermissionDenied("Buni faqat studiya egasi yoki menejeri o'zgartira oladi.")
    return membership


class StudioMePortfolioView(APIView):
    permission_classes = [IsStudioMember]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    access_notes = {
        "*": AccessNote(ownership=OWN_STUDIO),
        "post": AccessNote(ownership=OWN_STUDIO, conditions=(f"Ko'pi bilan {MAX_PORTFOLIO_IMAGES} ta rasm, har biri 5 MB gacha",)),
    }

    @extend_schema(
        summary="Studiya portfoliosi (rasmlar va reels, like / izoh soni bilan)",
        tags=["studio"],
        responses=PortfolioItemSerializer(many=True),
    )
    def get(self, request, studio_id):
        membership = _membership(request, studio_id)
        items = list(membership.studio.images.all())
        context = {"request": request, "engagement": services.engagement_map([i.pk for i in items])}
        return Response(PortfolioItemSerializer(items, many=True, context=context).data)

    @extend_schema(
        summary="Portfolioga rasm qo'shish",
        tags=["studio"],
        request={"multipart/form-data": StudioImageUploadSerializer},
        responses={201: StudioImageSerializer},
    )
    def post(self, request, studio_id):
        membership = _membership(request, studio_id)
        upload = StudioImageUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        image = services.add_portfolio_image(request, membership.studio, upload.validated_data["image"])
        return Response(StudioImageSerializer(image, context={"request": request}).data, status=status.HTTP_201_CREATED)


class StudioMeReelsView(APIView):
    permission_classes = [IsStudioMember]
    parser_classes = [MultiPartParser, FormParser]
    access_notes = {
        "*": AccessNote(
            ownership=OWN_STUDIO,
            conditions=(BADGE_ONLY, f"Ko'pi bilan {MAX_PORTFOLIO_REELS} ta vertikal video, 1–90 soniya"),
        )
    }

    @extend_schema(
        summary="Portfolioga reels (vertikal video) qo'shish",
        tags=["studio"],
        request={"multipart/form-data": ReelUploadSerializer},
        responses={201: StudioImageSerializer},
    )
    def post(self, request, studio_id):
        membership = _membership(request, studio_id)
        upload = ReelUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        data = upload.validated_data
        item = services.add_portfolio_reel(
            request, membership.studio, data["video"], data.get("poster"), data.get("caption", "")
        )
        return Response(StudioImageSerializer(item, context={"request": request}).data, status=status.HTTP_201_CREATED)


class StudioMePortfolioImageView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {"*": AccessNote(ownership=OWN_STUDIO)}

    def _item(self, request, studio_id, image_id):
        membership = _membership(request, studio_id)
        return get_object_or_404(StudioImage, pk=image_id, studio=membership.studio)

    @extend_schema(
        summary="Portfolio ishining izohini (caption) o'zgartirish",
        tags=["studio"],
        request=PortfolioItemUpdateSerializer,
        responses=StudioImageSerializer,
    )
    def patch(self, request, studio_id, image_id):
        item = self._item(request, studio_id, image_id)
        body = PortfolioItemUpdateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        item = services.update_portfolio_item(request, item, body.validated_data["caption"])
        return Response(StudioImageSerializer(item, context={"request": request}).data)

    @extend_schema(summary="Portfoliodan rasm / videoni o'chirish", tags=["studio"], responses={204: None})
    def delete(self, request, studio_id, image_id):
        services.delete_portfolio_image(request, self._item(request, studio_id, image_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudioMeCommentsView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {"*": AccessNote(ownership=OWN_STUDIO)}

    @extend_schema(summary="Portfolio ishiga yozilgan izohlar", tags=["studio"], responses=CommentSerializer(many=True))
    def get(self, request, studio_id, image_id):
        membership = _membership(request, studio_id)
        item = get_object_or_404(StudioImage, pk=image_id, studio=membership.studio)
        return Response(CommentSerializer(services.visible_comments(item)[:200], many=True).data)


class StudioMeCommentView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {"*": AccessNote(ownership=OWN_STUDIO)}

    @extend_schema(summary="Izohni o'chirish (studiya moderatsiyasi)", tags=["studio"], responses={204: None})
    def delete(self, request, studio_id, image_id, comment_id):
        membership = _membership(request, studio_id)
        comment = get_object_or_404(
            StudioPortfolioComment, pk=comment_id, item_id=image_id, item__studio=membership.studio
        )
        services.delete_comment(request, comment, by_studio=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudioMeScheduleView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {"*": AccessNote(ownership=OWN_STUDIO)}

    @extend_schema(
        summary="Studiya grafigi (marosimlar, band va dam olish kunlari)",
        tags=["studio"],
        parameters=[
            OpenApiParameter("from", OpenApiTypes.DATE, required=True),
            OpenApiParameter("to", OpenApiTypes.DATE, required=True, description="Ko'pi bilan 62 kun."),
        ],
        responses=StudioPanelScheduleSerializer,
    )
    def get(self, request, studio_id):
        membership = _membership(request, studio_id)
        start, end = parse_range(request.query_params)
        data = services.schedule(membership.studio, start, end, with_notes=True)
        return Response(StudioPanelScheduleSerializer(data).data)

    @extend_schema(
        summary="Haftalik dam olish kunlari",
        tags=["studio"],
        request=OffWeekdaysSerializer,
        responses=OffWeekdaysSerializer,
    )
    def patch(self, request, studio_id):
        membership = _membership(request, studio_id)
        body = OffWeekdaysSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        studio = services.set_off_weekdays(request, membership.studio, body.validated_data["off_weekdays"])
        return Response({"off_weekdays": studio.off_weekdays})


class StudioMeScheduleDayView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {"*": AccessNote(ownership=OWN_STUDIO)}

    @extend_schema(
        summary="Kunni band / dam olish deb belgilash (status=null — tozalash)",
        tags=["studio"],
        request=DayStatusWriteSerializer,
        responses={204: None},
    )
    def put(self, request, studio_id, day):
        membership = _membership(request, studio_id)
        date = parse_date(day)
        body = DayStatusWriteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        services.set_day_status(
            request, membership.studio, date, body.validated_data["status"], body.validated_data.get("note", "")
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class StudioMeChatsView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {"*": AccessNote(ownership=OWN_STUDIO)}

    @extend_schema(summary="Mijozlar bilan suhbatlar", tags=["studio-chat"], responses=StudioConversationSerializer(many=True))
    def get(self, request, studio_id):
        membership = _membership(request, studio_id)
        conversations = list(chat.studio_conversations(membership.studio)[:200])
        context = {"last_messages": chat.last_messages(conversations)}
        return Response(StudioConversationSerializer(conversations, many=True, context=context).data)


class StudioMeChatView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {
        "*": AccessNote(ownership=OWN_STUDIO),
        "post": AccessNote(ownership=OWN_STUDIO, conditions=(BADGE_ONLY,)),
    }

    def _conversation(self, request, studio_id, conversation_id):
        membership = _membership(request, studio_id)
        conversation = get_object_or_404(
            StudioConversation.objects.select_related("studio", "user"), pk=conversation_id, studio=membership.studio
        )
        return membership, conversation

    @extend_schema(summary="Mijoz bilan suhbat (xabarlar)", tags=["studio-chat"], responses=StudioThreadSerializer)
    def get(self, request, studio_id, conversation_id):
        membership, conversation = self._conversation(request, studio_id, conversation_id)
        messages = chat.messages(conversation)
        chat.mark_read(conversation, by_studio=True)
        can_write = membership.role in StudioMembership.MANAGING_ROLES and services.has_badge(conversation.studio)
        data = {"id": conversation.pk, "customer": conversation.user, "can_write": can_write, "messages": messages}
        return Response(StudioThreadSerializer(data).data)

    @extend_schema(
        summary="Mijozga javob yozish",
        tags=["studio-chat"],
        request=ChatMessageWriteSerializer,
        responses={201: ChatMessageSerializer},
    )
    def post(self, request, studio_id, conversation_id):
        _, conversation = self._conversation(request, studio_id, conversation_id)
        body = ChatMessageWriteSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        message = chat.send_from_studio(request.user, conversation, body.validated_data["body"])
        return Response(ChatMessageSerializer(message).data, status=status.HTTP_201_CREATED)




# ------------------------------------------------------------ portfolio files
class PortfolioFileView(APIView):
    """Bytes of one portfolio file (Drive stream with HTTP Range, or the local file)."""

    permission_classes = [AllowAny]
    access_notes = {
        "*": AccessNote(
            conditions=(
                "Ommaga: faqat ko'rinadigan ishlar (reels — galichka faol bo'lsa); studiya a'zolari va "
                "studios.view ruxsatli xodimlar — barchasi",
                "HTTP Range qo'llab-quvvatlanadi (video uchun)",
            )
        )
    }

    def perform_content_negotiation(self, request, force=False):
        return super().perform_content_negotiation(request, force=True)

    def _can_see_hidden(self, request, studio) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role in ("SUPER_ADMIN", "ADMIN"):
            return user.has_admin_permission("studios.view")
        return services.active_memberships(user).filter(studio=studio).exists()

    @extend_schema(
        summary="Portfolio fayli (rasm, reels videosi yoki muqovasi)",
        tags=["studios-public"],
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY, 206: OpenApiTypes.BINARY},
    )
    def get(self, request, studio_id, item_id, part):
        from django.http import FileResponse, HttpResponse, StreamingHttpResponse

        from apps.media.viewing import _safe_range

        from . import portfolio_storage
        from .models import PortfolioKind, PortfolioStorage, Studio

        studio = get_object_or_404(Studio, pk=studio_id, deleted_at__isnull=True)
        item = StudioImage.objects.filter(studio=studio, pk=item_id).first()
        if item is None or part not in ("main", "poster") or (part == "poster" and item.kind != PortfolioKind.VIDEO):
            raise NotFound()
        public = studio.is_active and services.public_items(studio).filter(pk=item.pk).exists()
        if not public and not self._can_see_hidden(request, studio):
            raise NotFound()

        if item.storage == PortfolioStorage.LOCAL:
            field = item.video if part == "main" and item.kind == PortfolioKind.VIDEO else item.image
            if not field:
                raise NotFound()
            response = FileResponse(field.open("rb"))
        else:
            file_id = item.drive_poster_id if part == "poster" else item.drive_file_id
            mime = "image/webp" if part == "poster" or item.kind == PortfolioKind.IMAGE else item.mime_type
            stream = portfolio_storage.open_stream(file_id, _safe_range(request.headers.get("Range")))
            if stream.status == 416:
                stream.close()
                return HttpResponse(status=416)

            def body():
                try:
                    yield from stream.chunks
                finally:
                    stream.close()

            response = StreamingHttpResponse(body(), status=stream.status, content_type=mime or "application/octet-stream")
            for key, value in stream.headers.items():
                response[key] = value
            response["Accept-Ranges"] = "bytes"
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Disposition"] = "inline"
        return response


class StudioMeStorageView(APIView):
    permission_classes = [IsStudioMember]
    access_notes = {"*": AccessNote(ownership=OWN_STUDIO)}

    @extend_schema(summary="Portfolio joyi (ishlatilgan / ajratilgan)", tags=["studio"], responses=PortfolioUsageSerializer)
    def get(self, request, studio_id):
        from . import portfolio_storage

        membership = _membership(request, studio_id)
        return Response(PortfolioUsageSerializer(portfolio_storage.usage(membership.studio)).data)
