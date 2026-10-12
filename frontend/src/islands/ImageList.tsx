import { useRef, useState } from "react";
import {
    DndContext,
    PointerSensor,
    closestCenter,
    useSensor,
    useSensors,
    type DragEndEvent,
} from "@dnd-kit/core";
import {
    SortableContext,
    arrayMove,
    rectSortingStrategy,
    useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { uploadImage } from "../lib/upload";

type ImageRow = {
    id: string;
    image: string;
    uploading?: boolean;
};

type Props = {
    name: string;
    images?: unknown;
};

let nextId = 1;

function SortableImage({ row, onRemove }: { row: ImageRow; onRemove: (id: string) => void }) {
    const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
        id: row.id,
        disabled: row.uploading,
    });
    return (
        <div
            ref={setNodeRef}
            className="image-list-item"
            style={{ transform: CSS.Transform.toString(transform), transition }}
            {...attributes}
            {...listeners}
        >
            <img src={row.image} alt="" />
            {row.uploading ? (
                <span className="image-list-status">…</span>
            ) : (
                <button
                    type="button"
                    className="image-list-remove"
                    aria-label="Убрать"
                    onPointerDown={(event) => event.stopPropagation()}
                    onClick={(event) => {
                        event.stopPropagation();
                        onRemove(row.id);
                    }}
                >
                    ×
                </button>
            )}
        </div>
    );
}

export default function ImageList({ name, images }: Props) {
    const input = useRef<HTMLInputElement>(null);
    const [rows, setRows] = useState<ImageRow[]>(() => {
        let source = images;
        while (typeof source === "string") {
            try {
                source = JSON.parse(source);
            } catch {
                source = [];
            }
        }

        if (!Array.isArray(source)) return [];
        return source.flatMap((row) => {
            if (!row || typeof row !== "object") return [];
            const image = (row as { image?: unknown }).image;
            if (typeof image !== "string" || !image) return [];
            return [{ id: `image-${++nextId}`, image }];
        });
    });
    const [over, setOver] = useState(false);
    const [error, setError] = useState("");
    const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));
    const saved = rows.filter((row) => !row.uploading).map((row) => ({ image: row.image }));

    function onDragEnd(event: DragEndEvent) {
        const { active, over: target } = event;
        if (!target || active.id === target.id) return;
        setRows((current) => {
            const from = current.findIndex((row) => row.id === active.id);
            const to = current.findIndex((row) => row.id === target.id);
            if (from < 0 || to < 0) return current;
            return arrayMove(current, from, to);
        });
    }

    async function addFiles(files: File[]) {
        setError("");
        if (!files.length) return;

        const pending = files.map((file) => ({
            id: `image-${++nextId}`,
            image: URL.createObjectURL(file),
            uploading: true,
            file,
        }));
        setRows((current) => [...current, ...pending.map(({ file: _file, ...row }) => row)]);

        await Promise.all(
            pending.map(async (item) => {
                try {
                    const url = await uploadImage(item.file);
                    setRows((current) =>
                        current.map((row) => (row.id === item.id ? { id: row.id, image: url } : row)),
                    );
                } catch (reason) {
                    setRows((current) => current.filter((row) => row.id !== item.id));
                    setError(reason instanceof Error ? reason.message : "Не получилось загрузить картинку");
                } finally {
                    URL.revokeObjectURL(item.image);
                }
            }),
        );
    }

    return (
        <div
            className={over ? "image-list image-list-over" : "image-list"}
            onClick={(event) => {
                const target = event.target as HTMLElement;
                if (target.closest(".image-list-item")) return;
                input.current?.click();
            }}
            onDragOver={(event) => {
                if (![...event.dataTransfer.types].includes("Files")) return;
                event.preventDefault();
                setOver(true);
            }}
            onDragLeave={() => setOver(false)}
            onDrop={(event) => {
                if (![...event.dataTransfer.types].includes("Files")) return;
                event.preventDefault();
                setOver(false);
                void addFiles([...event.dataTransfer.files]);
            }}
        >
            <input type="hidden" name={name} value={JSON.stringify(saved)} />
            <input
                ref={input}
                type="file"
                multiple
                onChange={() => {
                    const files = [...(input.current?.files ?? [])];
                    if (input.current) input.current.value = "";
                    void addFiles(files);
                }}
            />
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
                <SortableContext items={rows.map((row) => row.id)} strategy={rectSortingStrategy}>
                    <div className="image-list-grid">
                        {rows.map((row) => (
                            <SortableImage
                                key={row.id}
                                row={row}
                                onRemove={(id) => setRows((current) => current.filter((item) => item.id !== id))}
                            />
                        ))}
                    </div>
                </SortableContext>
            </DndContext>
            {!rows.length && (
                <div className="image-list-hint">
                    <div>Перетащите картинки сюда</div>
                    <div className="image-list-hint-note">или нажмите, чтобы выбрать</div>
                </div>
            )}
            {error && <div className="form-error">{error}</div>}
        </div>
    );
}
