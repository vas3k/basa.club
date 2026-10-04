import { useState } from "react";

// Editable list of records. Submits a JSON array in a hidden input named `name`.
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

function parseRecords(records: unknown): unknown[] {
    if (typeof records === "string") {
        if (!records) return [];
        try {
            return parseRecords(JSON.parse(records));
        } catch {
            return [];
        }
    }
    return Array.isArray(records) ? records : [];
}

function coerce(field: Field, value: unknown): string {
    const text = typeof value === "string" ? value : "";
    if (field.kind !== "select") return text;
    const options = field.options ?? [];
    if (options.some((option) => option.value === text)) return text;
    return options[0]?.value ?? "";
}

function blankValues(fields: Field[]): Record<string, string> {
    const values: Record<string, string> = {};
    for (const field of fields) values[field.key] = coerce(field, "");
    return values;
}

function toRows(fields: Field[], records: unknown): Row[] {
    const rows = parseRecords(records).map((record) => {
        const values = blankValues(fields);
        if (record && typeof record === "object") {
            const source = record as Record<string, unknown>;
            for (const field of fields) values[field.key] = coerce(field, source[field.key]);
        }
        return { id: nextId++, values };
    });
    if (!rows.length) rows.push({ id: nextId++, values: blankValues(fields) });
    return rows;
}

function isFilled(fields: Field[], row: Row): boolean {
    return fields.some((field) => field.kind !== "select" && (row.values[field.key] ?? "").trim() !== "");
}

export default function RecordList({ name, label, addLabel = "Добавить", fields, records }: Props) {
    const [rows, setRows] = useState(() => toRows(fields, records));
    const payload = rows.filter((row) => isFilled(fields, row)).map((row) => row.values);

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
                onClick={() => setRows((current) => [...current, { id: nextId++, values: blankValues(fields) }])}
            >
                {addLabel}
            </button>
        </div>
    );
}
