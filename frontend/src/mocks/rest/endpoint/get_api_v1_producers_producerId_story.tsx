import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 生産者ストーリー取得API GET /api/v1/producers/:producerId/story
//
// 生産者1「山本農園」の公開ストーリー（学ぶページ）。未入力の項目は null
//
// 生産者または公開ストーリーが存在しない（404）:
//   { errorCode: 'STORY_NOT_FOUND', errorMsg: 'ストーリーが見つかりません。' }
const producerStory: RestMock = {
  method: 'GET',
  path: '/api/v1/producers/:producerId/story',
  status: 200,
  body: {
    id: 1,
    producerId: 1,
    category: { id: 1, name: '栽培方法' },
    title: '草生栽培で土の力を引き出す、樹上完熟のりんご',
    method:
      '草生栽培・減農薬（県基準の50%以下）。草生栽培で土の力を引き出し、農薬は県基準の半分以下。樹上で完熟させてから収穫します。',
    process:
      '春に花を摘んで実の数を絞り、秋は葉摘みと玉回しで色づけします。11月に樹上で完熟したものから一つずつ手で収穫し、選果して箱詰めします。',
    environment: null,
    reason: '祖父の代から続く園地を、次の世代にも残したいと思い会社を辞めて戻りました。',
    goal: '収穫体験と短期スタッフ受け入れで、りんご産地の担い手を増やしたい。',
    updatedAt: hoursFromNow(-24 * 7),
  },
};

export { producerStory };
