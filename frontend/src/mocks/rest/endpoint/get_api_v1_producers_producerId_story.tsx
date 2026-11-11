import type { Story } from '../../../types/story';
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

const additionalStories: Story[] = [
  { id: 12, producerId: 2, category: { id: 2, name: '生産の現場' }, title: '駿河湾の恵みを、毎日の食卓へ', method: '魚の状態を見ながら、一枚ずつ丁寧に干物に仕上げます。', process: '港に届いた魚を選び、下処理・塩漬け・乾燥を経て出荷します。', environment: '旬の魚を使い、地域の資源を大切にしています。', reason: '港と食卓をつなぐ仕事を、次の世代へ残したい。', goal: '見学や仕事の受け入れを通じて、水産業の仲間を増やしていきます。', updatedAt: hoursFromNow(-48) },
  { id: 23, producerId: 3, category: { id: 3, name: '暮らしと仕事' }, title: '牛とともに育つ、十勝の暮らし', method: '牛の体調と食事を毎日確認し、一頭ずつ向き合います。', process: '朝の搾乳から飼育管理まで、仲間と協力して牧場を支えます。', environment: null, reason: '広い土地で動物と暮らしながら、おいしい乳製品を届けたいと思いました。', goal: '牧場体験を通じて、酪農を身近に感じてもらうことが目標です。', updatedAt: hoursFromNow(-72) },
];
producerStory.handler = url => {
  const producerId = Number(url.pathname.split('/').at(-2));
  const story = producerId === 1 ? producerStory.body : additionalStories.find(story => story.producerId === producerId);
  return story ? { status: 200, body: story } : { status: 404, body: { errorCode: 'STORY_NOT_FOUND', errorMsg: 'ストーリーが見つかりません。' } };
};
