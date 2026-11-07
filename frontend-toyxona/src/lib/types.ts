/** Shapes returned by the Django API (see docs/openapi.yaml). Money is a decimal string. */

export type Role = "SUPER_ADMIN" | "ADMIN" | "STUDIO" | "VENUE_OWNER" | "USER";

export interface Me {
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
