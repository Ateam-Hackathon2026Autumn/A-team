import type { UserInfo } from './user';

export type ConsumerProfile = {
  phone: string | null;
  birthDate: string | null;
  prefectureId: number | null;
  interests: string[];
};
export type ConsumerAccount = { user: UserInfo; profile: ConsumerProfile };
export type ConsumerProfileInput = ConsumerProfile & { lastName: string; firstName: string };
