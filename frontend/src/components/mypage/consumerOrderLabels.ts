export const paymentLabels: Record<string, string> = {
  pending: 'お支払い待ち',
  paid: '支払い済み',
  failed: '決済失敗・期限切れ',
};
export const shipmentLabels: Record<string, string> = {
  unshipped: '発送準備中',
  shipped: '発送済み',
  delivered: 'お届け済み',
  canceled: 'キャンセル',
  cancel_requested: 'キャンセル申請中',
};
export const temperatureLabels: Record<string, string> = {
  normal: '常温',
  chilled: '冷蔵',
  frozen: '冷凍',
};
