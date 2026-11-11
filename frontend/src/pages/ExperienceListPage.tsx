import { useSearchParams } from "react-router";
import { getExperiences } from "../api/experienceApi";
import ExperienceCard from "../components/experiences/ExperienceCard";
import Button from "../components/ui/Button";
import { areas, ContentPage, ContentStatus, EmptyContent, fieldClass, panelClass } from "../components/ui/ContentPage";
import { usePublicContent } from "../hooks/usePublicContent";

export default function ExperienceListPage() {
  const state = usePublicContent(getExperiences);
  const [params, setParams] = useSearchParams();
  const update = (name: string, value: string) =>
    setParams((previous) => {
      const next = new URLSearchParams(previous);
      if (value) next.set(name, value);
      else next.delete(name);
      return next;
    });
  const items = (state.data ?? []).filter(
    (item) =>
      (!params.get("area") || item.areaId === Number(params.get("area"))) &&
      (!params.get("price") || item.priceAdult <= Number(params.get("price"))) &&
      (!params.get("month") || item.nextStartAt?.slice(0, 7) === params.get("month")) &&
      (!params.get("family") || item.familyOk) &&
      (!params.get("beginner") || item.beginnerOk) &&
      (!params.get("producerId") || item.producer.id === Number(params.get("producerId"))),
  );
  return (
    <ContentPage
      eyebrow="EXPERIENCES"
      title="畑へ、海へ、牧場へ。"
      intro="生産者が案内する、農業・漁業・畜産の体験プログラム。"
    >
      <section
        aria-label="体験の絞り込み"
        className={panelClass}
      >
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="text-sm font-bold">
            地域
            <select
              className={fieldClass}
              value={params.get("area") ?? ""}
              onChange={(event) => update("area", event.target.value)}
            >
              {areas.map((area, index) => (
                <option
                  key={area}
                  value={index || ""}
                >
                  {area}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-bold">
            開催月
            <input
              type="month"
              className={fieldClass}
              value={params.get("month") ?? ""}
              onChange={(event) => update("month", event.target.value)}
            />
          </label>
          <label className="text-sm font-bold">
            料金（大人1名）
            <select
              className={fieldClass}
              value={params.get("price") ?? ""}
              onChange={(event) => update("price", event.target.value)}
            >
              <option value="">すべての料金</option>
              <option value="3000">3,000円以下</option>
              <option value="5000">5,000円以下</option>
            </select>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-5">
          {[
            ["family", "親子参加OK"],
            ["beginner", "初心者歓迎"],
          ].map(([key, label]) => (
            <label
              key={key}
              className="flex min-h-11 items-center gap-2"
            >
              <input
                type="checkbox"
                checked={Boolean(params.get(key))}
                onChange={(event) => update(key, event.target.checked ? "1" : "")}
                className="size-5 accent-marche-green"
              />
              {label}
            </label>
          ))}
          <Button
            variant="outline"
            onClick={() => setParams({})}
          >
            条件をクリア
          </Button>
        </div>
        <p className="mb-0 text-xs text-marche-muted">開催月は各体験の次回開催日で絞り込みます。</p>
      </section>
      <ContentStatus {...state} />
      {!state.loading && !state.error && (
        <>
          <p
            role="status"
            className="my-6 font-bold"
          >
            {items.length}件の体験
          </p>
          {items.length ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <ExperienceCard
                  key={item.id}
                  experience={item}
                />
              ))}
            </div>
          ) : (
            <EmptyContent>
              <p>この条件の体験はまだありません。</p>
              <p>地域や開催月を広げてみてください。</p>
              <Button
                variant="outline"
                onClick={() => setParams({})}
              >
                すべての体験を見る
              </Button>
            </EmptyContent>
          )}
        </>
      )}
    </ContentPage>
  );
}
