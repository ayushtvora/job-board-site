"use client";

import { useEffect, useId, useRef, useState } from "react";
import styles from "./FilterSelect.module.css";

type Option = { value: string; label: string };

// A dropdown drawn in the page instead of a native <select>: browsers draw a
// native select's open list themselves, outside the page, so it can't use
// the page's web font (Firefox has no way to opt out of that).
export default function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const labelId = useId();
  const listId = useId();

  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: PointerEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  // Keep the highlighted option in view while moving through a long list.
  useEffect(() => {
    if (!open) return;
    listRef.current?.children[activeIndex]?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex]);

  function openList() {
    setActiveIndex(selectedIndex);
    setOpen(true);
  }

  function choose(index: number) {
    onChange(options[index].value);
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) {
        e.preventDefault();
        openList();
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, options.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      setActiveIndex(e.key === "Home" ? 0 : options.length - 1);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      choose(activeIndex);
    } else if (e.key === "Escape" || e.key === "Tab") {
      setOpen(false);
    } else if (e.key.length === 1) {
      // Typing a letter jumps to the next option starting with it, like a
      // native select.
      const key = e.key.toLowerCase();
      const count = options.length;
      for (let step = 1; step <= count; step++) {
        const i = (activeIndex + step) % count;
        if (options[i].label.toLowerCase().startsWith(key)) {
          setActiveIndex(i);
          break;
        }
      }
    }
  }

  return (
    <div className={styles.root} ref={rootRef}>
      <span id={labelId}>{label}</span>
      <div className={styles.control}>
        <button
          type="button"
          className={styles.button}
          role="combobox"
          aria-labelledby={labelId}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={listId}
          aria-activedescendant={open ? `${listId}-${activeIndex}` : undefined}
          onClick={() => (open ? setOpen(false) : openList())}
          onKeyDown={onKeyDown}
        >
          <span className={styles.buttonText}>{options[selectedIndex]?.label}</span>
          <span className={styles.chevron} aria-hidden="true">▾</span>
        </button>
        {open && (
          <ul className={styles.list} id={listId} role="listbox" aria-labelledby={labelId} ref={listRef}>
            {options.map((option, i) => (
              <li
                key={option.value}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === selectedIndex}
                className={`${styles.option} ${i === activeIndex ? styles.active : ""} ${
                  i === selectedIndex ? styles.selected : ""
                }`}
                onPointerEnter={() => setActiveIndex(i)}
                onClick={() => choose(i)}
              >
                {option.label}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
