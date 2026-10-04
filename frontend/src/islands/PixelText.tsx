import { useLayoutEffect, useRef } from "react";

type Props = {
    text: string;
};

const BLOCK_CSS_PX = 5;

export default function PixelText({ text }: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useLayoutEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        let cancelled = false;

        const paint = () => {
            if (cancelled) return;
            const parent = canvas.closest(".inline-block");
            const style = getComputedStyle(parent ?? document.body);
            const color = style.color || "#333";
            const fontFamily = style.fontFamily || "sans-serif";
            const dpr = window.devicePixelRatio || 1;
            const block = Math.max(2, Math.round(BLOCK_CSS_PX * dpr));
            const fontPx = Math.round(18 * dpr);

            const measure = document.createElement("canvas").getContext("2d");
            if (!measure) return;
            measure.font = `600 ${fontPx}px ${fontFamily}`;
            const textWidth = Math.ceil(measure.measureText(text).width);
            const srcW = Math.max(block, textWidth);
            const srcH = Math.ceil(fontPx * 1.25);

            const src = document.createElement("canvas");
            src.width = srcW;
            src.height = srcH;
            const source = src.getContext("2d", { willReadFrequently: true });
            if (!source) return;
            source.font = `600 ${fontPx}px ${fontFamily}`;
            source.fillStyle = color;
            source.textBaseline = "middle";
            source.fillText(text, 0, srcH / 2);

            const cols = Math.ceil(srcW / block);
            const rows = Math.ceil(srcH / block);
            canvas.width = cols * block;
            canvas.height = rows * block;
            canvas.style.width = `${canvas.width / dpr}px`;
            canvas.style.height = `${canvas.height / dpr}px`;

            const ctx = canvas.getContext("2d");
            if (!ctx) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = color;

            const pixels = source.getImageData(0, 0, srcW, srcH).data;
            for (let y = 0; y < rows; y++) {
                for (let x = 0; x < cols; x++) {
                    let alpha = 0;
                    let count = 0;
                    const x0 = x * block;
                    const y0 = y * block;
                    const x1 = Math.min(srcW, x0 + block);
                    const y1 = Math.min(srcH, y0 + block);
                    for (let py = y0; py < y1; py++) {
                        for (let px = x0; px < x1; px++) {
                            alpha += pixels[(py * srcW + px) * 4 + 3];
                            count++;
                        }
                    }
                    if (count > 0 && alpha / count > 48) {
                        ctx.fillRect(x0, y0, block, block);
                    }
                }
            }
        };

        paint();
        document.fonts.ready.then(paint);
        return () => {
            cancelled = true;
        };
    }, [text]);

    return <canvas ref={canvasRef} className="inline-block-secure-pixels" aria-hidden="true" />;
}
