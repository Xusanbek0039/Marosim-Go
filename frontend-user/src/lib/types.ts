/** Shapes returned by the Django API (see docs/openapi.yaml). Money is a decimal string. */

export type Role = "SUPER_ADMIN" | "ADMIN" | "STUDIO" | "VENUE_OWNER" | "USER";

export interface Me {
  is_verified: boolean;
  id: string;
  phone_number: string;
  is_phone_verified: boolean;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: Role;
  profile_picture: string | null;
  address: string;
  pinfl_masked: string | null;
  permissions: string[];
  last_login: string | null;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ---------------------------------------------------------------- ceremonies
export type CeremonyStatus = "DRAFT" | "UPLOADING" | "PROCESSING" | "READY" | "ARCHIVED";
export type ParticipantType = "BRIDE" | "GROOM" | "OTHER";
export type AccessStatus = "INVITED" | "ACTIVE" | "DECLINED" | "REVOKED";

export interface StudioBrief {
  id: string;
  name: string;
  profile_picture: string | null;
  address: string;
}

export interface MyStudio extends StudioBrief {
  description: string;
  is_active: boolean;
  created_at: string;
}

export interface MyStudioMembership {
  role: "OWNER" | "MANAGER" | "UPLOADER";
  can_manage: boolean;
  studio: MyStudio;
  ceremonies_count: number;
}

export interface Ceremony {
  id: string;
  studio: StudioBrief;
  title: string;
  event_type: string;
  event_date: string;
  description: string;
  status: CeremonyStatus;
  participants_summary: { invited: number; active: number };
  can_manage: boolean;
  created_at: string;
  updated_at: string;
}

export interface Participant {
  id: string;
  phone_number: string;
  participant_type: ParticipantType;
  access_status: AccessStatus;
  display_name: string | null;
  invited_at: string;
  responded_at: string | null;
}

export interface MyCeremony {
  id: string;
  title: string;
  event_type: string;
  event_date: string;
  description: string;
  status: CeremonyStatus;
  studio: StudioBrief;
  access_role: "OWNER" | "VIEWER";
  my_role: ParticipantType | null;
  participants: { participant_type: ParticipantType; owner_type: string; full_name: string }[];
}

export interface Invitation {
  id: string;
  requested_role: "OWNER" | "VIEWER";
  owner_type: string | null;
  access_duration: AccessDuration | "";
  participant_type: ParticipantType | null;
  ceremony_id: string;
  ceremony_title: string | null;
  event_date: string | null;
  studio_name: string | null;
  inviter_display: string | null;
  invited_at: string;
  expires_at: string;
  phone_verification_required: boolean;
  requires_owner_approval: boolean;
}

// ---------------------------------------------------------- media + sharing
export type AccessDuration = "24H" | "3D" | "1W" | "1M";

export interface MyMedia {
  id: string;
  kind: "PHOTO" | "VIDEO";
  mime_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  duration_ms: number | null;
  completed_at: string;
  can_download: boolean;
  /** Shown with the MarosimGo logo (no running subscription, or a viewer). */
  watermarked: boolean;
  /** Video: the logo copy is still being prepared. */
  processing: boolean;
  /** 0-100 while the logo copy is being made (null while still queued). */
  progress: number | null;
}

export interface CeremonyMembers {
  viewer_limit: number;
  owners: { id: string; owner_type: string; full_name: string; is_me: boolean; accepted_at: string }[];
  viewers: {
    id: string;
    full_name: string;
    granted_by_name: string | null;
    granted_by_me: boolean;
    can_revoke: boolean;
    accepted_at: string;
    expires_at: string | null;
  }[];
  pending_owner_requests: number;
}

export interface SentInvitation {
  id: string;
  identifier_type: "PHONE" | "PINFL";
  recipient_hint: string;
  requested_role: "OWNER" | "VIEWER";
  access_duration: AccessDuration | "";
  status: "PENDING" | "ACCEPTED" | "DECLINED" | "REVOKED" | "EXPIRED";
  is_mine: boolean;
  can_revoke: boolean;
  invited_at: string;
  expires_at: string;
}
