import { Link } from 'react-router';
import type { Experience } from '../../types/experience';
import { ContentImage } from '../ui/ContentPage';
import { dateLabel, yen } from '../ui/contentPageValues';
export default function ExperienceCard({
  experience: item,
}: {
  experience: Experience;
}) {
  return (
    <article className="overflow-hidden rounded-2xl border border-marche-line bg-white">
      <Link
        to={`/experiences/${item.id}`}
        aria-label={item.title}
        className="group block h-full text-marche-ink no-underline hover:bg-marche-sage/40 focus-visible:-outline-offset-3"
      >
        <ContentImage
          src={item.thumbnailUrl}
          alt={item.title}
          className="aspect-[4/3]"
        />
        <div className="p-5">
          <p className="m-0 text-sm text-marche-green">
            {item.nextStartAt ? dateLabel(item.nextStartAt) : '開催日調整中'}
          </p>
          <h2 className="my-3 font-serif text-xl group-hover:underline">
            {item.title}
          </h2>
          <p className="text-sm text-marche-muted">
            {item.prefectureName} {item.producer.city} ・{' '}
            {item.producer.businessName}
          </p>
          <p className="font-bold">
            {yen(item.priceAdult)}{' '}
            <span className="text-sm font-normal">／大人1名</span>
          </p>
          <div className="flex flex-wrap gap-2 text-xs text-marche-green">
            {item.familyOk && (
              <span className="rounded-full bg-marche-sage px-3 py-1">
                親子参加OK
              </span>
            )}
            {item.beginnerOk && (
              <span className="rounded-full bg-marche-sage px-3 py-1">
                初心者歓迎
              </span>
            )}
          </div>
        </div>
      </Link>
    </article>
  );
}
