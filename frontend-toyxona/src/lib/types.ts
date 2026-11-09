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

// -------------------------------------------------------------------- venues
export type Region =
  | "TASHKENT_CITY"
  | "TASHKENT"
  | "ANDIJAN"
  | "BUKHARA"
  | "FERGANA"
  | "JIZZAKH"
  | "KHOREZM"
  | "NAMANGAN"
  | "NAVOI"
  | "KASHKADARYA"
  | "KARAKALPAKSTAN"
  | "SAMARKAND"
  | "SIRDARYO"
  | "SURKHANDARYA";
export type VenueType = "BANQUET_HALL" | "RESTAURANT" | "CAFE" | "OUTDOOR" | "OTHER";
export type PublicationStatus = "PRIVATE" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "SUSPENDED";
export type MembershipRole = "OWNER" | "MANAGER" | "SCHEDULER" | "VIEWER";
export type Capability =
  | "VIEW"
  | "EDIT_PROFILE"
  | "MANAGE_HALLS"
  | "MANAGE_SCHEDULE"
  | "MANAGE_PRICING"
  | "MANAGE_BOOKINGS"
  | "REQUEST_PUBLICATION"
  | "MANAGE_MEMBERS";

export interface VenueHall {
  id: string;
  name: string;
  capacity: number;
  /** null = the venue's base_price applies. */
  base_price: string | null;
  effective_base_price: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface VenueImage {
  id: string;
  image: string;
  position: number;
  created_at: string;
}

export interface Venue {
  id: string;
  name: string;
  description: string;
  venue_type: VenueType;
  address: string;
  region: Region;
  district: string;
  latitude: string | null;
  longitude: string | null;
  phone_number: string;
  cover_image: string | null;
  capacity_min: number;
  capacity_max: number;
  base_price: string;
  currency: "UZS";
  is_active: boolean;
  publication_status: PublicationStatus;
  halls: VenueHall[];
  images: VenueImage[];
  membership_role: MembershipRole | null;
  membership_capabilities: Capability[];
  created_at: string;
  updated_at: string;
}

export interface VenueMember {
  id: string;
  user: { id: string; full_name: string; phone_number: string };
  role: MembershipRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
