import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// ストーリー登録・更新API PUT /api/v1/dashboard/story
//
// 全項目を置き換えて、保存後のストーリーを返す。更新は 200、初回登録は 201（status を 201 に変える）
//
// 公開条件を満たさない（本文5項目がすべて空など）（409）:
//   { errorCode: 'CONFLICT', errorMsg: '公開するには本文を1項目以上入力してください。' }
//
// 他の画面で先に更新されていた（412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '他の操作で更新されています。画面を再読み込みしてください。' }
const dashboardStoryUpsert: RestMock = {
  method: 'PUT',
  path: '/api/v1/dashboard/story',
  status: 200,
  body: {
    id: 1,
    producerId: 1,
    storyCategoryId: 1,
    title: '北アルプスの雪どけ水で育てる、蜜たっぷりのりんご',
    method:
      '草生栽培・減農薬（県基準の50%以下）。草生栽培で土の力を引き出し、農薬は県基準の半分以下。樹上で完熟させてから収穫します。',
    process:
      '春の摘花・摘果から秋の収穫まで、1本ずつ手作業で手入れしています。収穫したりんごはその日のうちに選果して出荷します。',
    environment:
      '園地の下草は刈り取って土に戻し、化学肥料に頼らない土づくりを続けています。',
    reason: '祖父の代から続く園地を、次の世代にも残したいと思い会社を辞めて戻りました。',
    goal: '収穫体験と短期スタッフ受け入れで、りんご産地の担い手を増やしたい。',
    publishStatus: 'public',
    category: {
      id: 1,
      name: '栽培方法',
    },
    updatedAt: hoursFromNow(0),
  },
};

export { dashboardStoryUpsert };
