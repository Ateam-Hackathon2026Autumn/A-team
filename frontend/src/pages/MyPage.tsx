import { Link } from 'react-router';
import { getConsumerAccount } from '../api/consumerAccountApi';
import { usePublicContent } from '../hooks/usePublicContent';
import { ContentPage, ContentStatus } from '../components/ui/ContentPage';
import { panelClass } from '../components/ui/contentPageValues';
import MyPageNavigation from '../components/mypage/MyPageNavigation';
const menus = [
  ['/mypage/orders', '注文履歴', 'ご注文とお届けの状況を確認する'],
  ['/mypage/favorites', 'お気に入り', '気になる商品や、応援したい生産者'],
  ['/mypage/experiences', '体験予約履歴', '畑や海で過ごす、次の楽しみ'],
  ['/mypage/jobs', '求人応募履歴', '応募したお仕事の選考状況'],
  ['/mypage/profile', 'プロフィール編集', 'あなたの情報と興味のあること'],
  ['/mypage/settings', 'アカウント設定', 'ログイン情報・ログアウト'],
];

export default function MyPage() {
  const state = usePublicContent(getConsumerAccount);
  return (
    <ContentPage
      eyebrow="MY PAGE"
      title="マイページ"
      intro="つくる人とのつながりを、ここから。"
    >
      <MyPageNavigation />
      <ContentStatus {...state} />
      {state.data && (
        <section className={`${panelClass} mb-8 flex items-center gap-5`}>
          <span
            aria-hidden="true"
            className="grid size-16 shrink-0 place-items-center rounded-full bg-marche-sage font-serif text-2xl text-marche-green"
          >
            {state.data.user.lastName.slice(0, 1)}
          </span>
          <div>
            <h2 className="m-0 font-serif text-xl">
              {state.data.user.lastName} {state.data.user.firstName} さん
            </h2>
            <p className="m-0 text-sm text-marche-muted">
              会員ID {state.data.user.id}
            </p>
          </div>
        </section>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {menus.map(([to, title, text]) => (
          <Link
            key={to}
            to={to}
            className={`${panelClass} text-marche-ink no-underline transition-colors hover:bg-marche-sage`}
          >
            <h2 className="m-0 font-serif text-xl">
              {title}{' '}
              <span
                aria-hidden="true"
                className="float-right text-marche-green"
              >
                →
              </span>
            </h2>
            <p className="mb-0 mt-3 text-sm text-marche-muted">{text}</p>
          </Link>
        ))}
      </div>
    </ContentPage>
  );
}
