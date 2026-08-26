import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Select } from "./Select";

const options = [{ value: "required", label: "必要" }, { value: "preferred", label: "加分" }];

describe("Select", () => {
  afterEach(cleanup);

  it("renders a placeholder and dismisses without changing on Escape or outside click", () => {
    const onChange = vi.fn();
    render(<div><Select value="" options={options} placeholder="选择优先级" onChange={onChange} aria-label="优先级" /><button>外部</button></div>);
    const trigger = screen.getByRole("combobox", { name: "优先级" });
    expect(trigger).toHaveTextContent("选择优先级");
    fireEvent.click(trigger);
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("button", { name: "外部" }));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("supports highlighted keyboard selection and exposes listbox semantics", () => {
    const onChange = vi.fn();
    render(<Select value="" options={options} placeholder="选择优先级" onChange={onChange} aria-label="优先级" />);
    const trigger = screen.getByRole("combobox", { name: "优先级" });
    fireEvent.click(trigger);
    fireEvent.keyDown(trigger, { key: "ArrowDown" });
    fireEvent.keyDown(trigger, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("preferred");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
