import { useState } from 'react';
import { getProducers } from '../api/producerApi';
import { usePublicContent } from '../hooks/usePublicContent';
import {
  ContentPage,
  ContentStatus,
  EmptyContent,
} from '../components/ui/ContentPage';
import { fieldClass, panelClass } from '../components/ui/contentPageValues';
import ProducerSummaryCard from '../components/producers/ProducerSummaryCard';
import { producerGenres } from '../components/producers/producerLabels';
import Button from '../components/ui/Button';

export default function ProducerListPage() {
  const state = usePublicContent(getProducers);
  const [region, setRegion] = useState('');
  const [genre, setGenre] = useState('');
  const [query, setQuery] = useState('');
  const producers = state.data?.filter(
    (p) =>
      (!region || p.prefectureName === region) &&
      (!genre || p.genre === genre) &&
      `${p.businessName} ${p.productionItems} ${p.city}`.includes(query.trim()),
  );
  return (
    <ContentPage
      eyebrow="PRODUCERS"
      title="つくる人に、会いにいこう。"
      intro="畑から、海から。食卓の向こうにいる生産者を探してみませんか。"
    >
      <div className={`${panelClass} mb-8 grid gap-4 sm:grid-cols-3`}>
        <label className="text-sm font-bold">
          キーワード
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="生産者名・生産品目"
            className={`${fieldClass} mt-2`}
          />
        </label>
        <label className="text-sm font-bold">
          地域
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className={`${fieldClass} mt-2`}
          >
            <option value="">すべての都道府県</option>
            {[...new Set(state.data?.map((p) => p.prefectureName) ?? [])].map(
              (name) => (
                <option key={name}>{name}</option>
              ),
            )}
          </select>
        </label>
        <label className="text-sm font-bold">
          ジャンル
          <select
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            className={`${fieldClass} mt-2`}
          >
            <option value="">すべてのジャンル</option>
            {Object.entries(producerGenres).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <ContentStatus {...state} />
      {producers && (
        <p role="status" className="text-sm text-marche-muted">
          {producers.length}件の生産者
        </p>
      )}
      {producers?.length === 0 && (
        <EmptyContent>
          <p>条件に合う生産者が見つかりませんでした。</p>
          <Button
            variant="outline"
            onClick={() => {
              setRegion('');
              setGenre('');
              setQuery('');
            }}
          >
            条件をリセット
          </Button>
        </EmptyContent>
      )}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {producers?.map((producer) => (
          <ProducerSummaryCard key={producer.id} producer={producer} />
        ))}
      </div>
    </ContentPage>
  );
}
