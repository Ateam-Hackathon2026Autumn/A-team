import { Link } from 'react-router';
import { ContentImage } from '../ui/ContentPage';
import type { ProducerSummary } from '../../types/producer';
import { producerGenres, producerBadges } from './producerLabels';

export default function ProducerSummaryCard({
  producer,
}: {
  producer: ProducerSummary;
}) {
  return (
    <article className="overflow-hidden rounded-2xl border border-solid border-marche-line bg-white">
      <Link
        to={`/producers/${producer.id}`}
        className="block h-full text-marche-ink no-underline hover:bg-marche-sage/40"
      >
        <ContentImage
          src={producer.coverImageUrl ?? producer.profileImageUrl}
          alt={`${producer.businessName}の風景`}
          className="aspect-[16/9]"
        />
        <div className="p-5">
          <p className="m-0 text-xs text-marche-muted">
            {producer.prefectureName} {producer.city} ·{' '}
            {producerGenres[producer.genre] ?? producer.genre}
          </p>
          <h2 className="mb-2 mt-3 font-serif text-xl">
            {producer.businessName}
          </h2>
          <p className="m-0 text-sm">{producer.productionItems}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {producer.badges.map((badge) => (
              <span
                key={badge}
                className="rounded-full bg-marche-sage px-3 py-1 text-xs font-bold text-marche-green"
              >
                {producerBadges[badge] ?? badge}
              </span>
            ))}
          </div>
          <p className="mb-0 mt-4 text-sm font-bold text-marche-green">
            つくる人を知る →
          </p>
        </div>
      </Link>
    </article>
  );
}
