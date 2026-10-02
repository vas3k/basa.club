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

import { isImageFile, uploadImage } from "../lib/upload";

const MAX_IMAGES = 10;

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

function rowId() {
    nextId += 1;
    return `image-${nextId}`;
}

function parseImages(images: unknown): ImageRow[] {
    if (typeof images === "string") {
        if (!images) return [];
        try {
            return parseImages(JSON.parse(images));
        } catch {
            return [];
        }
    }
    if (!Array.isArray(images)) return [];
    return images.flatMap((row) => {
        if (!row || typeof row !== "object") return [];
        const image = (row as { image?: unknown }).image;
        if (typeof image !== "string" || !image) return [];
        return [{ id: rowId(), image }];
    });
}

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
    const [rows, setRows] = useState(() => parseImages(images));
    const rowsRef = useRef(rows);
    rowsRef.current = rows;
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
        const imagesOnly = files.filter(isImageFile);
        if (imagesOnly.length !== files.length) {
            setError("Можно загрузить jpeg, png, bmp или webp");
        } else {
            setError("");
        }
        const room = MAX_IMAGES - rowsRef.current.filter((row) => !row.uploading).length;
        const accepted = imagesOnly.slice(0, Math.max(room, 0));
        if (accepted.length < imagesOnly.length) {
            setError("Слишком много картинок");
        }
        if (!accepted.length) return;

        const pending = accepted.map((file) => ({
            id: rowId(),
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
                accept="image/jpeg,image/png,image/bmp,image/webp"
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
            {!rows.length && <div className="image-list-hint">Перетащите фото сюда или нажмите, чтобы выбрать</div>}
            {error && <div className="form-error">{error}</div>}
        </div>
    );
}
