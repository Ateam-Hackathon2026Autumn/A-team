// 生産者申請の状態（最新の申請）
type ProducerApplicationStatus =
  | 'not_applied'
  | 'pending'
  | 'approved'
  | 'rejected';

// 生産者アカウントの状態（生産者レコードがない場合は null）
type ProducerAccountStatus = 'active' | 'suspended' | null;

// ログインユーザーの情報（API の User スキーマ）
type UserInfo = {
  id: number;
  email: string;
  lastName: string;
  firstName: string;
  // 申請が approved かつアカウントが active の場合のみ true
  isProducer: boolean;
  producerApplicationStatus: ProducerApplicationStatus;
  producerAccountStatus: ProducerAccountStatus;
  emailVerified: boolean;
};

export type { ProducerAccountStatus, ProducerApplicationStatus, UserInfo };
