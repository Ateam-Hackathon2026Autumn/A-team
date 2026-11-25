// 都道府県（ID は JIS コード順。API の prefectureId と同じ 1〜47）
const PREFECTURE_NAMES = [
  '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
  '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
  '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
  '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県',
  '奈良県', '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
  '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
  '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県',
] as const;

const PREFECTURES = PREFECTURE_NAMES.map((name, index) => ({
  id: index + 1,
  name,
}));

// 該当しない ID は空文字
function prefectureName(prefectureId: number): string {
  return PREFECTURE_NAMES[prefectureId - 1] ?? '';
}

export { PREFECTURES, prefectureName };
