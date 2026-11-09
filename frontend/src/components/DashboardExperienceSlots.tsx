import { useEffect, useState, type FormEvent } from 'react';

import ApiError from '../api/apiError';
import {
  createExperienceSlot,
  deleteExperienceSlot,
  getExperienceSlots,
  newIdempotencyKey,
  updateExperienceSlot,
} from '../api/dashboardExperienceApi';
import type {
  ExperienceSlot,
  ExperienceSlotStatus,
  ExperienceSlotUpdateInput,
} from '../types/experience';
import {
  formatDateTime,
  formatDuration,
  slotStatusLabels,
  splitJstDateTime,
  toJstDateTime,
} from '../utils/experienceFormat';
import DashboardButton from './DashboardButton';
import { Field, controlBorder, controlClassName, describedBy } from './DashboardFormParts';

const MAX_DURATION_MIN = 10080;
const MAX_INT = 2147483647;

// 予約枠の入力欄の値
type SlotFormValues = {
  date: string;
  time: string;
  durationMin: string;
  capacity: string;
};

type SlotFormErrors = Partial<Record<keyof SlotFormValues, string>>;

const emptySlotValues: SlotFormValues = {
  date: '',
  time: '10:00',
  durationMin: '120',
  capacity: '10',
};

const slotStatusBadgeClassNames: Record<ExperienceSlotStatus, string> = {
  open: 'bg-marche-sage text-marche-green',
  closed: 'bg-marche-line text-marche-ink',
  canceled: 'bg-marche-red/10 text-marche-red',
};

function isWholeNumber(value: string) {
  return /^\d+$/.test(value) && Number(value) <= MAX_INT;
}

function validateSlot(values: SlotFormValues, checkFuture: boolean): SlotFormErrors {
  const errors: SlotFormErrors = {};

  if (values.date === '') {
    errors.date = '開催日を選んでください。';
  }

  if (values.time === '') {
    errors.time = '開始時刻を選んでください。';
  }

  if (
    checkFuture &&
    errors.date === undefined &&
    errors.time === undefined &&
    new Date(toJstDateTime(values.date, values.time)).getTime() <= Date.now()
  ) {
    errors.date = '現在より後の日時を指定してください。';
  }

  if (
    !isWholeNumber(values.durationMin) ||
    Number(values.durationMin) < 1 ||
    Number(values.durationMin) > MAX_DURATION_MIN
  ) {
    errors.durationMin = `所要時間は1〜${MAX_DURATION_MIN}分の半角数字で入力してください。`;
  }

  if (!isWholeNumber(values.capacity) || Number(values.capacity) < 1) {
    errors.capacity = '定員は1以上の半角数字で入力してください。';
  }

  return errors;
}

function toSlotValues(slot: ExperienceSlot): SlotFormValues {
  const { date, time } = splitJstDateTime(slot.startAt);

  return {
    date,
    time,
    durationMin: String(slot.durationMin),
    capacity: String(slot.capacity),
  };
}

function isPast(slot: ExperienceSlot) {
  return new Date(slot.startAt).getTime() <= Date.now();
}

// 予約枠の日時・所要時間・定員の入力欄（追加と編集で共通）
function SlotFields({
  idPrefix,
  values,
  errors,
  onChange,
  timeLocked,
}: {
  idPrefix: string;
  values: SlotFormValues;
  errors: SlotFormErrors;
  onChange: (name: keyof SlotFormValues, value: string) => void;
  // 予約がある枠は日時・所要時間を変えられない
  timeLocked: boolean;
}) {
  const input = (
    name: keyof SlotFormValues,
    props: { type: string; inputMode?: 'numeric'; disabled?: boolean },
  ) => {
    const id = `${idPrefix}-${name}`;

    return (
      <input
        id={id}
        type={props.type}
        inputMode={props.inputMode}
        disabled={props.disabled}
        value={values[name]}
        onChange={(event) => onChange(name, event.target.value)}
        aria-invalid={errors[name] !== undefined}
        aria-describedby={describedBy(id, false, errors[name])}
        className={`${controlClassName} ${controlBorder(errors[name])} disabled:bg-marche-canvas disabled:text-marche-muted`}
      />
    );
  };

  return (
    <div className="grid gap-4 sm:grid-cols-4">
      <Field id={`${idPrefix}-date`} label="開催日" required error={errors.date}>
        {input('date', { type: 'date', disabled: timeLocked })}
      </Field>
      <Field id={`${idPrefix}-time`} label="開始時刻" required error={errors.time}>
        {input('time', { type: 'time', disabled: timeLocked })}
      </Field>
      <Field
        id={`${idPrefix}-durationMin`}
        label="所要時間（分）"
        required
        error={errors.durationMin}
      >
        {input('durationMin', { type: 'text', inputMode: 'numeric', disabled: timeLocked })}
      </Field>
      <Field id={`${idPrefix}-capacity`} label="定員（人）" required error={errors.capacity}>
        {input('capacity', { type: 'text', inputMode: 'numeric' })}
      </Field>
    </div>
  );
}

type DashboardExperienceSlotsProps = {
  experienceId: number;
  // 予約枠を変更すると体験の ETag も変わるため、親で体験を取り直す
  onChanged: () => void;
};

// 体験の予約枠の一覧・追加・編集・受付停止・中止・削除
function DashboardExperienceSlots({ experienceId, onChanged }: DashboardExperienceSlotsProps) {
  const [slots, setSlots] = useState<ExperienceSlot[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [reloadCount, setReloadCount] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<number | 'new' | null>(null);

  const [addValues, setAddValues] = useState<SlotFormValues>(emptySlotValues);
  const [addErrors, setAddErrors] = useState<SlotFormErrors>({});
  const [addStatus, setAddStatus] = useState<'open' | 'closed'>('open');

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValues, setEditValues] = useState<SlotFormValues>(emptySlotValues);
  const [editErrors, setEditErrors] = useState<SlotFormErrors>({});

  useEffect(() => {
    let isActive = true;

    getExperienceSlots(experienceId)
      .then((data) => {
        if (isActive) {
          setSlots(data.items);
          setLoadError(false);
        }
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          window.location.replace('/signin');
          return;
        }

        if (isActive) {
          setLoadError(true);
        }
      });

    return () => {
      isActive = false;
    };
  }, [experienceId, reloadCount]);

  const reloadSlots = () => {
    setSlots(null);
    setLoadError(false);
    setEditingId(null);
    setReloadCount((count) => count + 1);
  };

  const replaceSlot = (updated: ExperienceSlot) => {
    setSlots(
      (current) =>
        current?.map((slot) => (slot.id === updated.id ? updated : slot)) ?? null,
    );
  };

  // 予約枠の操作の共通部分（通信中の管理・エラー表示・体験の取り直し）
  const runAction = async (
    id: number | 'new',
    action: () => Promise<string>,
  ): Promise<boolean> => {
    setActionError(null);
    setNotice(null);
    setPendingId(id);

    try {
      setNotice(await action());
      onChanged();
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        window.location.replace('/signin');
        return false;
      }

      if (error instanceof ApiError && error.status === 412) {
        setActionError(
          '他の画面で予約枠が更新されていたため、最新の内容を読み込み直しました。もう一度操作してください。',
        );
        reloadSlots();
      } else if (error instanceof ApiError && error.status === 404) {
        setActionError('予約枠が見つかりませんでした。最新の内容を読み込み直しました。');
        reloadSlots();
      } else if (error instanceof ApiError) {
        setActionError(error.message);
      } else {
        setActionError('通信に失敗しました。時間をおいて、もう一度お試しください。');
      }

      return false;
    } finally {
      setPendingId(null);
    }
  };

  const handleAdd = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const errors = validateSlot(addValues, true);
    setAddErrors(errors);

    if (Object.keys(errors).length > 0) {
      return;
    }

    const succeeded = await runAction('new', async () => {
      const created = await createExperienceSlot(
        experienceId,
        {
          startAt: toJstDateTime(addValues.date, addValues.time),
          durationMin: Number(addValues.durationMin),
          capacity: Number(addValues.capacity),
          status: addStatus,
        },
        newIdempotencyKey(),
      );

      setSlots((current) =>
        [...(current ?? []), created].sort(
          (a, b) =>
            new Date(a.startAt).getTime() - new Date(b.startAt).getTime() || a.id - b.id,
        ),
      );

      return `${formatDateTime(created.startAt)} の予約枠を追加しました。`;
    });

    if (succeeded) {
      // 時刻・所要時間・定員は続けて追加しやすいよう残し、日付だけ空にする
      setAddValues((current) => ({ ...current, date: '' }));
    }
  };

  const startEdit = (slot: ExperienceSlot) => {
    setEditingId(slot.id);
    setEditValues(toSlotValues(slot));
    setEditErrors({});
    setActionError(null);
    setNotice(null);
  };

  const handleEditSave = async (slot: ExperienceSlot) => {
    const timeLocked = slot.reservedCount > 0;
    const original = toSlotValues(slot);
    const timeChanged =
      editValues.date !== original.date ||
      editValues.time !== original.time ||
      editValues.durationMin !== original.durationMin;

    const errors = validateSlot(editValues, !timeLocked && timeChanged);

    if (
      errors.capacity === undefined &&
      Number(editValues.capacity) < slot.reservedCount
    ) {
      errors.capacity = `定員は予約人数（${slot.reservedCount}人）以上にしてください。`;
    }

    setEditErrors(errors);

    if (Object.keys(errors).length > 0) {
      return;
    }

    // 変えた項目だけ送る（予約がある枠の日時を送ると 409 になるため）
    const input: ExperienceSlotUpdateInput = {};

    if (!timeLocked && (editValues.date !== original.date || editValues.time !== original.time)) {
      input.startAt = toJstDateTime(editValues.date, editValues.time);
    }

    if (!timeLocked && editValues.durationMin !== original.durationMin) {
      input.durationMin = Number(editValues.durationMin);
    }

    if (editValues.capacity !== original.capacity) {
      input.capacity = Number(editValues.capacity);
    }

    if (Object.keys(input).length === 0) {
      setEditingId(null);
      return;
    }

    const succeeded = await runAction(slot.id, async () => {
      replaceSlot(await updateExperienceSlot(experienceId, slot, input));

      return '予約枠を変更しました。';
    });

    if (succeeded) {
      setEditingId(null);
    }
  };

  const handleStatusChange = (slot: ExperienceSlot, status: ExperienceSlotStatus) => {
    if (
      status === 'canceled' &&
      !window.confirm(
        `${formatDateTime(slot.startAt)} の予約枠を中止します。中止した枠は元に戻せません。よろしいですか？`,
      )
    ) {
      return;
    }

    runAction(slot.id, async () => {
      replaceSlot(await updateExperienceSlot(experienceId, slot, { status }));

      return status === 'open'
        ? '予約の受付を再開しました。'
        : status === 'closed'
          ? '予約の受付を停止しました。'
          : '予約枠を中止しました。';
    });
  };

  const handleDelete = (slot: ExperienceSlot) => {
    if (
      !window.confirm(
        `${formatDateTime(slot.startAt)} の予約枠を削除します。元に戻せません。よろしいですか？`,
      )
    ) {
      return;
    }

    runAction(slot.id, async () => {
      await deleteExperienceSlot(experienceId, slot);
      setSlots((current) => current?.filter(({ id }) => id !== slot.id) ?? null);

      return '予約枠を削除しました。';
    });
  };

  const renderSlot = (slot: ExperienceSlot) => {
    const isPending = pendingId === slot.id;
    const past = isPast(slot);
    const hasReservations = slot.reservedCount > 0;

    if (editingId === slot.id) {
      return (
        <li
          key={slot.id}
          className="box-border flex flex-col gap-4 rounded-xl border border-solid border-marche-green bg-white p-4"
        >
          <SlotFields
            idPrefix={`slot-${slot.id}`}
            values={editValues}
            errors={editErrors}
            timeLocked={hasReservations}
            onChange={(name, value) => {
              setEditValues((current) => ({ ...current, [name]: value }));
              setEditErrors((current) => ({ ...current, [name]: undefined }));
            }}
          />
          {hasReservations && (
            <p className="m-0 text-xs text-marche-muted">
              予約がある枠は、日時と所要時間を変更できません。
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <DashboardButton
              variant="secondary"
              size="sm"
              disabled={isPending}
              onClick={() => setEditingId(null)}
            >
              キャンセル
            </DashboardButton>
            <DashboardButton size="sm" disabled={isPending} onClick={() => handleEditSave(slot)}>
              {isPending ? '保存中…' : '変更を保存'}
            </DashboardButton>
          </div>
        </li>
      );
    }

    return (
      <li
        key={slot.id}
        className={`box-border flex flex-col gap-3 rounded-xl border border-solid border-marche-line p-4 sm:flex-row sm:items-center ${past || slot.status === 'canceled' ? 'bg-marche-canvas' : 'bg-white'}`}
      >
        <div className="min-w-0 flex-1">
          <p className="m-0 flex flex-wrap items-center gap-2 font-bold">
            {formatDateTime(slot.startAt)}
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-bold ${slotStatusBadgeClassNames[slot.status]}`}
            >
              {slotStatusLabels[slot.status]}
            </span>
            {past && slot.status !== 'canceled' && (
              <span className="rounded-full bg-marche-line px-2 py-0.5 text-xs font-bold text-marche-muted">
                終了
              </span>
            )}
          </p>
          <p className="m-0 mt-1 text-sm text-marche-muted">
            {formatDuration(slot.durationMin)} ・ 予約 {slot.reservedCount} / 定員 {slot.capacity}人
            {slot.status !== 'canceled' && `（残り ${slot.remainingCapacity}人）`}
          </p>
        </div>

        {slot.status !== 'canceled' && (
          <div className="flex flex-wrap gap-2">
            {!past && (
              <DashboardButton
                variant="secondary"
                size="sm"
                disabled={isPending}
                onClick={() => startEdit(slot)}
              >
                編集
              </DashboardButton>
            )}
            {slot.status === 'open' ? (
              <DashboardButton
                variant="secondary"
                size="sm"
                disabled={isPending}
                onClick={() => handleStatusChange(slot, 'closed')}
              >
                受付を停止
              </DashboardButton>
            ) : (
              !past && (
                <DashboardButton
                  variant="secondary"
                  size="sm"
                  disabled={isPending}
                  onClick={() => handleStatusChange(slot, 'open')}
                >
                  受付を再開
                </DashboardButton>
              )
            )}
            {!hasReservations && !past && (
              <DashboardButton
                variant="danger"
                size="sm"
                disabled={isPending}
                onClick={() => handleStatusChange(slot, 'canceled')}
              >
                中止
              </DashboardButton>
            )}
            <DashboardButton
              variant="danger"
              size="sm"
              disabled={isPending}
              onClick={() => handleDelete(slot)}
            >
              削除
            </DashboardButton>
          </div>
        )}
      </li>
    );
  };

  return (
    <section
      aria-labelledby="experience-slots-heading"
      className="box-border flex flex-col gap-5 rounded-2xl border border-solid border-marche-line bg-white p-5 md:p-6"
    >
      <div>
        <h2 id="experience-slots-heading" className="m-0 font-serif text-lg font-bold">
          予約枠
        </h2>
        <p className="m-0 mt-1 text-xs text-marche-muted">
          開催日時と定員ごとに予約枠を作ります。お客さまは受付中の枠から申し込めます。
        </p>
      </div>

      {actionError !== null && (
        <p role="alert" className="m-0 text-sm font-bold text-marche-red">
          {actionError}
        </p>
      )}
      {notice !== null && (
        <p role="status" className="m-0 text-sm font-bold text-marche-green">
          {notice}
        </p>
      )}

      {loadError ? (
        <div role="alert" className="text-sm">
          <p className="m-0 font-bold text-marche-red">予約枠を読み込めませんでした。</p>
          <DashboardButton variant="secondary" size="sm" onClick={reloadSlots} className="mt-3">
            再読み込み
          </DashboardButton>
        </div>
      ) : slots === null ? (
        <div aria-busy="true" className="h-20 animate-pulse rounded-xl bg-marche-canvas" />
      ) : slots.length === 0 ? (
        <p className="m-0 rounded-xl bg-marche-canvas p-4 text-sm text-marche-muted">
          まだ予約枠がありません。下のフォームから追加してください。
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">{slots.map(renderSlot)}</ul>
      )}

      <form
        noValidate
        onSubmit={handleAdd}
        className="box-border flex flex-col gap-4 rounded-xl bg-marche-canvas p-4"
      >
        <h3 className="m-0 text-sm font-bold">予約枠を追加</h3>
        <SlotFields
          idPrefix="slot-new"
          values={addValues}
          errors={addErrors}
          timeLocked={false}
          onChange={(name, value) => {
            setAddValues((current) => ({ ...current, [name]: value }));
            setAddErrors((current) => ({ ...current, [name]: undefined }));
          }}
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={addStatus === 'closed'}
              onChange={(event) => setAddStatus(event.target.checked ? 'closed' : 'open')}
              className="m-0 size-4 accent-marche-green"
            />
            受付停止の状態で追加する
          </label>
          <DashboardButton type="submit" size="sm" disabled={pendingId === 'new'}>
            {pendingId === 'new' ? '追加中…' : '予約枠を追加'}
          </DashboardButton>
        </div>
      </form>
    </section>
  );
}

export default DashboardExperienceSlots;
