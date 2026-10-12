import { useState } from "react";

// `records` may be an array or a JSON string (Django's JSONField prepares a string).

type Option = {
    value: string;
    label: string;
};

type Field = {
    key: string;
    kind: "text" | "select";
    placeholder?: string;
    maxLength?: number;
    muted?: boolean;
    options?: Option[];
};

type Row = {
    id: number;
    values: Record<string, string>;
};

type Props = {
    name: string;
    label?: string;
    addLabel?: string;
    fields: Field[];
    records?: unknown;
};

let nextId = 1;

export default function RecordList({ name, label, addLabel = "Добавить", fields, records }: Props) {
    const defaults: Record<string, string> = {};
    for (const field of fields) {
        const options = field.options ?? [];
        defaults[field.key] = "";
        if (field.kind === "select" && !options.some((option) => option.value === "")) {
            defaults[field.key] = options[0]?.value ?? "";
        }
    }

    const [rows, setRows] = useState<Row[]>(() => {
        let source = records;
        while (typeof source === "string") {
            try {
                source = JSON.parse(source);
            } catch {
                source = [];
            }
        }

        const initial = (Array.isArray(source) ? source : []).map((record) => {
            const values = { ...defaults };
            if (record && typeof record === "object") {
                for (const field of fields) {
                    const value = record[field.key];
                    const text = typeof value === "string" ? value : "";
                    const options = field.options ?? [];
                    values[field.key] = text;
                    if (field.kind === "select" && !options.some((option) => option.value === text)) {
                        values[field.key] = options[0]?.value ?? "";
                    }
                }
            }
            return { id: nextId++, values };
        });
        return initial.length ? initial : [{ id: nextId++, values: { ...defaults } }];
    });
    const payload = rows
        .filter((row) => fields.some((field) => field.kind !== "select" && (row.values[field.key] ?? "").trim() !== ""))
        .map((row) => row.values);

    function update(id: number, key: string, value: string) {
        setRows((current) =>
            current.map((row) => (row.id === id ? { ...row, values: { ...row.values, [key]: value } } : row)),
        );
    }

    return (
        <div className="form-group record-list">
            {label && <div className="form-section-title">{label}</div>}
            <input type="hidden" name={name} value={JSON.stringify(payload)} />
            {rows.map((row) => (
                <div className="record-list-row" key={row.id}>
                    {fields.map((field) =>
                        field.kind === "select" ? (
                            <select
                                key={field.key}
                                className="record-list-type"
                                value={row.values[field.key] ?? ""}
                                onChange={(event) => update(row.id, field.key, event.target.value)}
                            >
                                {(field.options ?? []).map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                        ) : (
                            <input
                                key={field.key}
                                type="text"
                                className={field.muted ? "record-list-comment" : "record-list-text"}
                                placeholder={field.placeholder}
                                maxLength={field.maxLength}
                                autoComplete="off"
                                value={row.values[field.key] ?? ""}
                                onChange={(event) => update(row.id, field.key, event.target.value)}
                            />
                        ),
                    )}
                    <button
                        type="button"
                        className="button button-inverted button-icon record-list-remove"
                        aria-label="Удалить"
                        onClick={() => setRows((current) => current.filter((item) => item.id !== row.id))}
                    >
                        ×
                    </button>
                </div>
            ))}
            <button
                type="button"
                className="button button-inverted button-small record-list-add"
                onClick={() => setRows((current) => [...current, { id: nextId++, values: { ...defaults } }])}
            >
                {addLabel}
            </button>
        </div>
    );
}
