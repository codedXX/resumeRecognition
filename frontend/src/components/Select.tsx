import { forwardRef, useEffect, useId, useRef, useState } from "react";

export type SelectOption = { value: string; label: string };

type SelectProps = {
  value: string;
  options: SelectOption[];
  placeholder: string;
  onChange: (value: string) => void;
  "aria-label"?: string;
  "aria-describedby"?: string;
  className?: string;
};

export const Select = forwardRef<HTMLButtonElement, SelectProps>(function Select({ value, options, placeholder, onChange, "aria-label": ariaLabel, "aria-describedby": ariaDescribedBy, className = "" }, ref) {
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(() => Math.max(0, options.findIndex((option) => option.value === value)));
  const rootRef = useRef<HTMLDivElement>(null);
  const listId = useId();
  const selected = options.find((option) => option.value === value);

  useEffect(() => {
    const closeWhenOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", closeWhenOutside);
    document.addEventListener("click", closeWhenOutside);
    return () => { document.removeEventListener("mousedown", closeWhenOutside); document.removeEventListener("click", closeWhenOutside); };
  }, []);

  useEffect(() => {
    const selectedIndex = options.findIndex((option) => option.value === value);
    if (selectedIndex >= 0) setHighlighted(selectedIndex);
  }, [options, value]);

  const choose = (option: SelectOption) => {
    onChange(option.value);
    setOpen(false);
    setHighlighted(options.findIndex((item) => item.value === option.value));
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        setHighlighted(Math.max(0, options.findIndex((option) => option.value === value)));
        return;
      }
      setHighlighted((current) => {
        const next = event.key === "ArrowDown" ? current + 1 : current - 1;
        return Math.min(Math.max(next, 0), Math.max(options.length - 1, 0));
      });
      return;
    }
    if (event.key === "Enter" && open) {
      event.preventDefault();
      const option = options[highlighted];
      if (option) choose(option);
    }
  };

  return <div ref={rootRef} className={`custom-select ${className}`.trim()}>
    <button ref={ref} type="button" className="custom-select-trigger" role="combobox" aria-label={ariaLabel} aria-describedby={ariaDescribedBy} aria-expanded={open} aria-controls={listId} aria-haspopup="listbox" onClick={() => { setOpen((current) => !current); setHighlighted(Math.max(0, options.findIndex((option) => option.value === value))); }} onKeyDown={handleKeyDown}>
      <span className={selected ? "custom-select-value" : "custom-select-placeholder"}>{selected?.label ?? placeholder}</span>
      <span className="custom-select-chevron" aria-hidden="true">⌄</span>
    </button>
    {open && <ul id={listId} role="listbox" className="custom-select-menu" aria-label={ariaLabel}>
      {options.map((option, index) => <li key={option.value} id={`${listId}-${option.value}`} role="option" aria-selected={option.value === value} className={`custom-select-option ${index === highlighted ? "is-highlighted" : ""}`} onMouseDown={(event) => event.preventDefault()} onClick={() => choose(option)}>{option.label}</li>)}
    </ul>}
  </div>;
});
