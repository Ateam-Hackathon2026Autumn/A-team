import type { ProducerGenre } from './dashboardProfile';

export type ProducerApplicationStatusValue =
  'pending' | 'approved' | 'rejected' | 'returned';

export type ProducerApplicationInput = {
  businessName: string;
  representativeName: string;
  genre: ProducerGenre;
  prefectureId: number;
  city: string;
  productionItems: string;
  intro: string;
  acceptsExperience: boolean;
  recruiting: boolean;
  careerStartYear?: number | null;
  foundedYear?: number | null;
  profileImage?: string | null;
  coverImage?: string | null;
  applicationReason?: string | null;
};

export type ProducerApplicationChanges = Partial<ProducerApplicationInput>;

export type ProducerApplicationResubmitInput = {
  applicationId: number;
  changes: ProducerApplicationChanges;
};

export type ProducerApplicationAccepted = {
  message: string;
  producerId: number;
  applicationId: number;
  approvalStatus: ProducerApplicationStatusValue;
  applicationStatus: ProducerApplicationStatusValue;
  publishStatus: 'draft' | 'public' | 'private' | 'suspended';
  isProducer: boolean;
  submittedAt: string;
};

export type MyProducerApplicationProducer = {
  businessName: string;
  representativeName: string;
  genre: ProducerGenre;
  prefectureId: number;
  city: string;
  productionItems: string;
  intro: string;
  acceptsExperience: boolean;
  recruiting: boolean;
  careerStartYear: number | null;
  foundedYear: number | null;
  profileImage: string | null;
  coverImage: string | null;
  profileImageUrl: string | null;
  coverImageUrl: string | null;
  applicationReason: string | null;
};

export type MyProducerApplication = {
  applicationId: number;
  producerId: number;
  status: ProducerApplicationStatusValue;
  reviewComment: string | null;
  submittedAt: string;
  reviewedAt: string | null;
  canResubmit: boolean;
  producer: MyProducerApplicationProducer;
};
