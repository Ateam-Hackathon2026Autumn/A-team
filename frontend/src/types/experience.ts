export type PageResult<T> = { items: T[]; total: number; page: number; pageSize: number; totalPages: number };
export type Experience = {
  id: number; title: string; areaId: number; prefectureName: string;
  priceAdult: number; priceChild: number | null; familyOk: boolean; beginnerOk: boolean;
  thumbnailUrl: string | null; nextStartAt: string | null;
  producer: { id: number; businessName: string; city: string };
};
export type PublicExperienceSlot = { id: number; startAt: string; durationMin: number; capacity: number; remainingCapacity: number; quoteToken: string };
export type PublicExperienceFlowItem = { time: string; text: string };
export type ExperienceDetail = Experience & {
  description: string; images: { id: number; url: string; sortOrder: number }[];
  place: string; ageCondition: string; flow: PublicExperienceFlowItem[] | null; belongings: string[]; notes: string[];
  cancelPolicy: string; slots: PageResult<PublicExperienceSlot>;
};
export type ExperienceApplyInput = {
  slotId: number; quoteToken: string; adultCount: number; childCount: number;
  representativeName: string; phone: string; message: string; policyAgreed: boolean;
};
export type ExperienceReceipt = { id: number; reservationNo: string; totalAmount: number };

export type ExperienceApplicationStatus = 'applied' | 'confirmed' | 'canceled' | 'attended';

export type MyExperienceApplication = {
  id: number;
  reservationNo: string;
  experience: {
    id: number;
    title: string | null;
    isPublic: boolean;
  };
  slot: {
    id: number;
    startAt: string;
    durationMin: number;
    status: 'open' | 'closed' | 'canceled';
  };
  adultCount: number;
  childCount: number;
  infantCount: number;
  totalAmount: number;
  status: ExperienceApplicationStatus;
  cancellable?: boolean;
  cancelDeadlineAt?: string | null;
  createdAt: string;
};

