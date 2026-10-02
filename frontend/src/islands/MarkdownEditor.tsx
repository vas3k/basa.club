import EasyMDE from "easymde";
import "easymde/dist/easymde.min.css";
import { useEffect, useRef } from "react";

type Props = {
  name: string;
  value?: string;
  label?: string;
  placeholder?: string;
};

export default function MarkdownEditor({
  name,
  value = "",
  label,
  placeholder,
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

    return () => editor.toTextArea();
  }, []);

  return (
    <div className="form-group">
      {label && <label htmlFor={`id_${name}`}>{label}</label>}
      <textarea
        ref={textareaRef}
        id={`id_${name}`}
        name={name}
        defaultValue={value}
      />
    </div>
  );
}
