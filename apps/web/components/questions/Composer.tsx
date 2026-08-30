"use client";

import { useEffect, useId, useRef, type KeyboardEvent } from "react";

import type { Dictionary } from "@/lib/i18n/dictionary";

const MAX_TEXTAREA_HEIGHT_PX = 200;

function SendIcon() {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true">
      <path d="M2.5 10L17 3.5l-4.5 13-3-6-6-.5z" />
    </svg>
  );
}

export function Composer({
  value,
  onChange,
  onSubmit,
  disabled,
  maxLength,
  error,
  dict,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  maxLength: number;
  error?: string | null;
  dict: Dictionary["questions"];
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const questionId = useId();
  const errorId = useId();
  const nearLimit = value.length >= maxLength * 0.9;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }, [value]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (!disabled && value.trim()) onSubmit();
    }
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (!disabled && value.trim()) onSubmit();
      }}
      aria-busy={disabled}
      className="flex flex-col gap-2 rounded-card border border-hairline bg-surface p-3 shadow-card transition-shadow focus-within:border-accent/40 focus-within:shadow-card-hover"
    >
      <label htmlFor={questionId} className="sr-only">
        {dict.composerLabel}
      </label>
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          id={questionId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={maxLength}
          rows={1}
          placeholder={dict.composerPlaceholder}
          aria-describedby={error ? errorId : undefined}
          className="max-h-[200px] min-h-[1.75rem] flex-1 resize-none overflow-y-auto bg-transparent py-1 text-sm text-ink placeholder:text-ink-subtle focus:outline-none"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label={dict.sendAriaLabel}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-white transition-colors hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-40 motion-safe:active:scale-[0.98]"
        >
          <SendIcon />
        </button>
      </div>
      <div className="flex items-center justify-between gap-3">
        <p aria-live="polite" className="sr-only">
          {disabled ? dict.askingLive : ""}
        </p>
        {error ? (
          <p id={errorId} role="alert" className="text-xs font-medium text-red-700">
            {error}
          </p>
        ) : (
          <span />
        )}
        <p className={`text-xs ${nearLimit ? "font-medium text-amber-700" : "text-ink-subtle"}`}>
          {value.length}/{maxLength}
        </p>
      </div>
    </form>
  );
}
