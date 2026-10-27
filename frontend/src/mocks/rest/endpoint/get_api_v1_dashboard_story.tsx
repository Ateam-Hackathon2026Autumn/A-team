import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// ストーリー取得API GET /api/v1/dashboard/story
//
// ログイン中の生産者（山本農園）のストーリー（1生産者1件）。本文はプレーンテキスト、未入力は null
//
// まだストーリーを登録していない（404）:
//   { errorCode: 'STORY_NOT_FOUND', errorMsg: 'ストーリーはまだ登録されていません。' }
const dashboardStory: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/story',
  status: 200,
  body: {
    id: 1,
    producerId: 1,
    storyCategoryId: 1,
    title: '北アルプスの雪どけ水で育てる、蜜たっぷりのりんご',
    // 栽培方法・こだわり
    method:
      '草生栽培・減農薬（県基準の50%以下）。草生栽培で土の力を引き出し、農薬は県基準の半分以下。樹上で完熟させてから収穫します。',
    process:
      '春の摘花・摘果から秋の収穫まで、1本ずつ手作業で手入れしています。収穫したりんごはその日のうちに選果して出荷します。',
    environment:
      '園地の下草は刈り取って土に戻し、化学肥料に頼らない土づくりを続けています。',
    // 就農した理由
    reason: '祖父の代から続く園地を、次の世代にも残したいと思い会社を辞めて戻りました。',
    // 今後の目標
    goal: '収穫体験と短期スタッフ受け入れで、りんご産地の担い手を増やしたい。',
    publishStatus: 'public',
    category: {
      id: 1,
      name: '栽培方法',
    },
    updatedAt: hoursFromNow(-24 * 7),
  },
};

export { dashboardStory };
