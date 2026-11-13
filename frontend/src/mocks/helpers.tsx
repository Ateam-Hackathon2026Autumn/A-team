// mocks/rest/endpoint/ の各ファイルから使うヘルパー

// 今日から指定日数後の日付（YYYY-MM-DD）を返却
//
// 体験の開催日や求人の勤務日などは固定の日付を書くと過去日になってしまうため、
// 「今日から◯日後」で作る（負の値で過去日）
function daysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);

  return date.toISOString().slice(0, 10);
}

// 現在時刻から指定時間後の ISO 文字列を返却（負の値で過去）
function hoursFromNow(hours: number): string {
  return new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
}

export { daysFromNow, hoursFromNow };
