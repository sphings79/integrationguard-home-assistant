import { css } from "lit";

/**
 * Shared styling. Everything is expressed through Home Assistant's own CSS
 * variables so the panel follows the active theme, including dark mode,
 * without shipping a second design language.
 */
export const sharedStyles = css`
  :host {
    --ig-gap: 16px;
    --ig-radius: var(--ha-card-border-radius, 12px);
    --ig-border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.25));
    display: block;
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, inherit);
  }

  .card {
    background: var(--card-background-color, #fff);
    border-radius: var(--ig-radius);
    box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0, 0, 0, 0.12));
    padding: var(--ig-gap);
    margin-bottom: var(--ig-gap);
  }

  .card.flush {
    padding: 0;
    overflow: hidden;
  }

  h2 {
    font-size: 1.25rem;
    font-weight: 500;
    margin: 0 0 12px;
  }

  h3 {
    font-size: 1rem;
    font-weight: 500;
    margin: 0 0 8px;
  }

  p.hint {
    color: var(--secondary-text-color);
    font-size: 0.875rem;
    margin: 4px 0 0;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .row.wrap {
    flex-wrap: wrap;
  }

  .spacer {
    flex: 1;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: var(--ig-gap);
  }

  label.field {
    display: block;
    margin-bottom: 14px;
  }

  label.field > span {
    display: block;
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
    margin-bottom: 4px;
  }

  input[type="text"],
  input[type="number"],
  input[type="time"],
  select {
    width: 100%;
    box-sizing: border-box;
    padding: 9px 10px;
    border: var(--ig-border);
    border-radius: 8px;
    background: var(--secondary-background-color, transparent);
    color: var(--primary-text-color);
    font: inherit;
    font-size: 0.9375rem;
  }

  input:focus,
  select:focus {
    outline: 2px solid var(--primary-color);
    outline-offset: -1px;
  }

  .checkbox {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 12px;
    cursor: pointer;
  }

  .checkbox input {
    margin: 2px 0 0;
    accent-color: var(--primary-color);
    width: 18px;
    height: 18px;
    flex-shrink: 0;
  }

  .checkbox span {
    font-size: 0.9375rem;
    line-height: 1.35;
  }

  button {
    font: inherit;
    font-size: 0.9375rem;
    font-weight: 500;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    cursor: pointer;
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  button.secondary {
    background: transparent;
    color: var(--primary-color);
    border: var(--ig-border);
  }

  button.danger {
    background: transparent;
    color: var(--error-color, #db4437);
    border: var(--ig-border);
  }

  button.plain {
    background: transparent;
    color: var(--secondary-text-color);
    padding: 6px 8px;
  }

  button:hover {
    filter: brightness(1.08);
  }

  button:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border-radius: 999px;
    border: var(--ig-border);
    font-size: 0.8125rem;
    cursor: pointer;
    background: transparent;
    color: var(--primary-text-color);
    user-select: none;
  }

  .chip[data-selected="true"] {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }

  .chip ha-icon {
    --mdc-icon-size: 16px;
  }

  .list-item {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px var(--ig-gap);
    border-bottom: var(--ig-border);
  }

  .list-item:last-child {
    border-bottom: none;
  }

  .list-item .title {
    font-size: 0.9375rem;
    font-weight: 500;
  }

  .list-item .subtitle {
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
    margin-top: 2px;
  }

  .empty {
    text-align: center;
    padding: 40px 20px;
    color: var(--secondary-text-color);
  }

  .empty ha-icon {
    --mdc-icon-size: 48px;
    opacity: 0.4;
    margin-bottom: 12px;
  }

  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
    background: var(--secondary-background-color, rgba(127, 127, 127, 0.15));
    color: var(--secondary-text-color);
  }

  /* Badges that carry a status colour of their own need readable text on it. */
  .badge.solid {
    color: var(--text-primary-color, #fff);
    white-space: nowrap;
  }

  .suffixed {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .suffixed input {
    flex: 1;
    min-width: 0;
  }

  .suffix {
    color: var(--secondary-text-color);
    font-size: 0.875rem;
    white-space: nowrap;
  }

  .error {
    color: var(--error-color, #db4437);
    font-size: 0.875rem;
    margin: 8px 0 0;
  }
`;

/** Maps Home Assistant's label colour names to a usable CSS colour. */
export const COLORS: Record<string, string> = {
  primary: "var(--primary-color, #03a9f4)",
  accent: "var(--accent-color, #ff9800)",
  red: "#f44336",
  pink: "#e91e63",
  purple: "#926bc7",
  "deep-purple": "#6e41ab",
  indigo: "#3f51b5",
  blue: "#2196f3",
  "light-blue": "#03a9f4",
  cyan: "#00bcd4",
  teal: "#009688",
  green: "#4caf50",
  "light-green": "#8bc34a",
  lime: "#cddc39",
  yellow: "#ffeb3b",
  amber: "#ffc107",
  orange: "#ff9800",
  "deep-orange": "#ff6f22",
  brown: "#795548",
  grey: "#9e9e9e",
  "blue-grey": "#607d8b",
  black: "#000000",
  white: "#ffffff",
};

/** Return a CSS colour for a Home Assistant colour name. */
export function colorOf(name: string | null | undefined): string {
  if (!name) return "var(--secondary-text-color)";
  return COLORS[name] ?? "var(--secondary-text-color)";
}
