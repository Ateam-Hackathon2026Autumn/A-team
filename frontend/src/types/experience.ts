export type PageResult<T> = { items: T[]; total: number; page: number; pageSize: number; totalPages: number };
export type Experience = {
  id: number; title: string; areaId: number; prefectureName: string;
  priceAdult: number; priceChild: number | null; familyOk: boolean; beginnerOk: boolean;
  thumbnailUrl: string | null; nextStartAt: string | null;
  producer: { id: number; businessName: string; city: string };
};
export type PublicExperienceSlot = { id: number; startAt: string; durationMin: number; capacity: number; remainingCapacity: number; bookingDeadlineAt: string; bookable: boolean };
export type PublicExperienceFlowItem = { time: string; text: string };
export type ExperienceDetail = Experience & {
  description: string; images: { id: number; url: string; sortOrder: number }[];
  place: string; ageCondition: string | null; flow: PublicExperienceFlowItem[] | null; belongings: string[] | null; notes: string[] | null;
  cancelPolicy: string; slots: PageResult<PublicExperienceSlot>;
};
export type ExperienceApplyInput = {
  slotId: number; adultCount: number; childCount: number; infantCount: number;
  lastName: string; firstName: string; phone: string; message: string | null;
  agreedToCancelPolicy: boolean; eligibilityConfirmed: boolean; expectedTotalAmount: number;
};
export type ExperienceReceipt = {
  id: number; reservationNo: string; experienceId: number; slotId: number;
  adultCount: number; childCount: number; infantCount: number; representativeName: string;
  phone: string; message: string | null; totalAmount: number; status: 'confirmed';
  policyAgreedAt: string; createdAt: string;
};
