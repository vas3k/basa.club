import EasyMDE from "easymde";
import "easymde/dist/easymde.min.css";
import { useEffect, useRef } from "react";

type Props = {
  name: string;
  value?: string;
  label?: string;
  placeholder?: string;
  maxLength?: number;
};

type EditorChange = {
  from: { line: number; ch: number };
  to: { line: number; ch: number };
  text: string[];
  cancel: () => void;
  update?: (
    from: { line: number; ch: number },
    to: { line: number; ch: number },
    text: string[],
  ) => void;
};

export default function MarkdownEditor({
  name,
  value = "",
  label,
  placeholder,
  maxLength,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!textareaRef.current) return;

    const editor = new EasyMDE({
      element: textareaRef.current,
      initialValue: value,
      placeholder,
      forceSync: true,
      spellChecker: false,
      status: false,
      autoDownloadFontAwesome: false,
      toolbar: [
        "bold",
        "italic",
        "heading",
        "|",
        "quote",
        "unordered-list",
        "ordered-list",
        "|",
        "link",
        "|",
        "preview",
      ],
    });

    const limit = maxLength ?? 0;
    if (limit > 0) {
      const mirror = editor.codemirror as {
        getValue: () => string;
        indexFromPos: (position: { line: number; ch: number }) => number;
        on: (
          event: "beforeChange",
          handler: (instance: unknown, change: EditorChange) => void,
        ) => void;
      };
      mirror.on("beforeChange", (_instance, change) => {
        const current = mirror.getValue();
        const removed = mirror.indexFromPos(change.to) - mirror.indexFromPos(change.from);
        const inserted = change.text.join("\n");
        if (current.length - removed + inserted.length <= limit) return;
        const room = limit - (current.length - removed);
        if (room <= 0 || !change.update) {
          change.cancel();
          return;
        }
        change.update(change.from, change.to, inserted.slice(0, room).split("\n"));
      });
    }

    return () => editor.toTextArea();
  }, []);

  return (
    <div className="form-group">
      {label && <label htmlFor={`id_${name}`}>{label}</label>}
      <textarea
        ref={textareaRef}
        id={`id_${name}`}
        name={name}
        maxLength={maxLength}
        defaultValue={value}
      />
    </div>
  );
}
