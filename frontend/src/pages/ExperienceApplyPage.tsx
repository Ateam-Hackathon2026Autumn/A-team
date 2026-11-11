import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router';
import { applyExperience, getExperience } from '../api/experienceApi';
import Button from '../components/ui/Button';
import FormField from '../components/ui/FormField';
import { ContentPage, ContentStatus, dateLabel, timeLabel, fieldClass, panelClass, textLinkClass, yen } from '../components/ui/ContentPage';
import { USE_MOCK } from '../config/env';
import { usePublicContent } from '../hooks/usePublicContent';
import type { ExperienceReceipt } from '../types/experience';

export default function ExperienceApplyPage() {
  const { experienceId } = useParams();
  return <ExperienceForm key={experienceId} id={Number(experienceId)} />;
}
function ExperienceForm({ id }: { id: number }) {
  const loader = useCallback((signal: AbortSignal) => getExperience(id, signal), [id]);
  const state = usePublicContent(loader);
  const [slotId, setSlotId] = useState('');
  const [adult, setAdult] = useState('1');
  const [child, setChild] = useState('0');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [step, setStep] = useState<'input' | 'confirm'>('input');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [receipt, setReceipt] = useState<ExperienceReceipt | null>(null);
  const locked = useRef(false);
  const formPanel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (step === 'confirm' || receipt) formPanel.current?.focus();
  }, [step, receipt]);
  const item = state.data;
  const slots = item?.slots.items.filter(slot => slot.remainingCapacity > 0 && new Date(slot.startAt).getTime() > Date.now()) ?? [];
  const selected = slots.find(slot => slot.id === Number(slotId));
  const adultCount = Number(adult);
  const childCount = Number(child);
  const total = item ? adultCount * item.priceAdult + childCount * (item.priceChild ?? 0) : 0;
  function validate() {
    const next: Record<string, string> = {};
    if (!selected) next.slot = '開催日を選択してください。';
    if (!adult.trim() || !Number.isSafeInteger(adultCount) || adultCount < 1) next.people = '大人は1名以上の整数で入力してください。';
    if (!child.trim() || !Number.isSafeInteger(childCount) || childCount < 0 || (item?.priceChild === null && childCount > 0)) next.people = '子どもの人数を確認してください。';
    if (selected && adultCount + childCount > selected.remainingCapacity) next.people = `残り枠（${selected.remainingCapacity}名）を超えています。人数を減らしてください。`;
    if (!name.trim()) next.name = '代表者氏名を入力してください。';
    const normalizedPhone = phone.normalize('NFKC').replace(/[() ー−-]/g, '');
    if (!/^\+?[0-9]{10,15}$/.test(normalizedPhone)) next.phone = '電話番号を確認してください（数字10〜15桁、ハイフン可）。';
    if (!agreed) next.agreed = 'キャンセルポリシーと注意事項への同意が必要です。';
    setErrors(next);
    return Object.keys(next).length === 0;
  }
  async function submit() {
    if (locked.current || !validate() || !selected) return;
    locked.current = true; setSending(true); setError('');
    try {
      setReceipt(await applyExperience(id, { slotId: selected.id, quoteToken: selected.quoteToken, adultCount, childCount, representativeName: name.trim(), phone: phone.trim(), message: message.trim(), policyAgreed: agreed }));
    } catch (cause) { setError(cause instanceof Error ? cause.message : '申込できませんでした。'); }
    finally { locked.current = false; setSending(false); }
  }
  return <ContentPage eyebrow="EXPERIENCE APPLICATION" title="体験への参加申込">
    <Link to={`/experiences/${id}`} className={textLinkClass}>← 体験詳細</Link><ContentStatus {...state} />
    {item && <div ref={formPanel} tabIndex={-1} className="mx-auto mt-5 max-w-3xl">
      <p className="font-serif text-xl font-bold">{item.title}</p>
      {receipt ? <section role="status" className={panelClass}><h2 className="font-serif text-2xl">{USE_MOCK ? 'デモ申込を受け付けました' : '申込を受け付けました'}</h2><p>予約番号：{receipt.reservationNo}</p><p>合計：{yen(receipt.totalAmount)}</p><p>実際の予約・決済・メール送信は行いません。</p><Link to="/experiences" className={textLinkClass}>体験一覧へ戻る →</Link></section> : !slots.length ? <p role="status" className={panelClass}>現在申し込める開催枠はありません。</p> : <>
        <ol aria-label="申込の進行状況" className="flex list-none gap-4 p-0 text-sm"><li aria-current={step === 'input' ? 'step' : undefined} className={step === 'input' ? 'font-bold text-marche-green' : ''}>1. 内容を入力</li><li aria-current={step === 'confirm' ? 'step' : undefined} className={step === 'confirm' ? 'font-bold text-marche-green' : ''}>2. 内容を確認</li></ol>
        <form noValidate className={panelClass} onSubmit={event => { event.preventDefault(); if (step === 'input') { if (validate()) { setStep('confirm'); setError(''); } } else void submit(); }}>
          {step === 'input' ? <>
            <h2 className="font-serif text-xl">参加内容</h2>
            <label htmlFor="slot" className="block font-bold">開催日</label><select id="slot" className={fieldClass} value={slotId} required aria-invalid={Boolean(errors.slot)} aria-describedby={errors.slot ? 'slot-error' : undefined} onChange={event => setSlotId(event.target.value)}><option value="">開催日を選択</option>{slots.map(slot => <option key={slot.id} value={slot.id}>{dateLabel(slot.startAt)} {timeLabel(slot.startAt)}〜 ／残り{slot.remainingCapacity}名</option>)}</select>
            {errors.slot && <p id="slot-error" role="alert" className="text-marche-red">{errors.slot}</p>}
            <div className="grid gap-4 sm:grid-cols-2"><FormField name="adult" label="大人の人数" type="number" min="1" max={selected ? String(selected.remainingCapacity) : undefined} value={adult} onChange={setAdult} error={errors.people} />{item.priceChild !== null && <FormField name="child" label="子どもの人数" type="number" min="0" max={selected ? String(selected.remainingCapacity) : undefined} value={child} onChange={setChild} />}</div>
            <p className="text-sm">対象：{item.ageCondition}。大人{yen(item.priceAdult)}{item.priceChild !== null && ` ／子ども${yen(item.priceChild)}`}</p>
            <FormField name="representative" label="代表者氏名" autoComplete="name" maxLength={100} value={name} onChange={setName} error={errors.name} />
            <FormField name="phone" label="電話番号" type="tel" autoComplete="tel" maxLength={20} value={phone} onChange={setPhone} error={errors.phone} />
            <label htmlFor="message" className="mb-2 mt-5 block font-bold">生産者へのメッセージ（任意）</label><textarea id="message" className={fieldClass} rows={4} maxLength={2000} value={message} onChange={event => setMessage(event.target.value)} />
            <h3 className="mt-6 text-base">キャンセルポリシー</h3><p>{item.cancelPolicy}</p><h3 className="text-base">注意事項</h3><ul className="pl-5">{item.notes.map(note => <li key={note}>{note}</li>)}</ul>
            <label className="flex min-h-11 items-start gap-3"><input type="checkbox" className="mt-2 size-5 shrink-0 accent-marche-green" checked={agreed} aria-invalid={Boolean(errors.agreed)} aria-describedby={errors.agreed ? 'agreed-error' : undefined} onChange={event => setAgreed(event.target.checked)} />キャンセルポリシーと注意事項に同意します</label>{errors.agreed && <p id="agreed-error" role="alert" className="text-marche-red">{errors.agreed}</p>}
          </> : <section aria-label="申込内容の確認"><h2 tabIndex={-1} className="font-serif text-xl">申込内容の確認</h2><p>{selected && `${dateLabel(selected.startAt)} ${timeLabel(selected.startAt)}〜`}</p><p>場所：{item.place}</p><p>大人{adultCount}名 ／子ども{childCount}名</p><p>代表者：{name}<br />電話番号：{phone}</p><p className="whitespace-pre-wrap">メッセージ：{message || 'なし'}</p><p>キャンセルポリシーと注意事項：同意済み</p></section>}
          <p className="mt-6 border-t border-marche-line pt-4 text-xl font-bold" role="status">合計：{Number.isFinite(total) && total >= 0 ? yen(total) : '人数を確認してください'}</p>
          {error && <p role="alert" className="text-marche-red">{error}</p>}
          {!USE_MOCK && <p className="text-marche-red">実際の申込送信は準備中です。</p>}
          <div className="mt-6 flex flex-wrap gap-3">{step === 'confirm' && <Button disabled={sending} variant="outline" onClick={() => { setStep('input'); setError(''); }}>入力内容を修正</Button>}<Button type="submit" disabled={sending || (step === 'confirm' && !USE_MOCK)}>{sending ? '送信中…' : step === 'input' ? '申込内容を確認する' : 'デモ申込を送信する'}</Button></div>
        </form>
      </>}
    </div>}
  </ContentPage>;
}
