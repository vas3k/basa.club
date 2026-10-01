import { useState } from "react";

import type { CategoryOption } from "../types";

type Props = {
    categories: CategoryOption[];
    category?: string;
    subcategory?: string;
};

export default function CategoryPicker({ categories, category = "", subcategory = "" }: Props) {
    const [categoryId, setCategoryId] = useState(category);
    const [subcategoryId, setSubcategoryId] = useState(subcategory);

    const subcategories = categories.find((c) => c.id === categoryId)?.children ?? [];

    return (
        <div className="form-row">
            <div className="form-group">
                <label htmlFor="id_category">Категория</label>
                <select
                    id="id_category"
                    name="category"
                    required
                    value={categoryId}
                    onChange={(event) => {
                        setCategoryId(event.target.value);
                        setSubcategoryId("");
                    }}
                >
                    <option value="" disabled>
                        Выберите категорию
                    </option>
                    {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                            {c.icon} {c.name}
                        </option>
                    ))}
                </select>
            </div>

            <div className="form-group">
                <label htmlFor="id_subcategory">Подкатегория</label>
                <select
                    id="id_subcategory"
                    name="subcategory"
                    required
                    value={subcategoryId}
                    disabled={!categoryId}
                    onChange={(event) => setSubcategoryId(event.target.value)}
                >
                    <option value="" disabled>
                        Выберите подкатегорию
                    </option>
                    {subcategories.map((c) => (
                        <option key={c.id} value={c.id}>
                            {c.name}
                        </option>
                    ))}
                </select>
            </div>
        </div>
    );
}
