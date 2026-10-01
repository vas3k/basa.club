import type { ComponentType } from "react";

type IslandModule = { default: ComponentType<Record<string, unknown>> };

// Lazy: each island (and React itself) is loaded only on pages that use it
const islands = import.meta.glob<IslandModule>("../islands/*.tsx");

export async function mountIslands(root: ParentNode = document) {
    const elements = [...root.querySelectorAll<HTMLElement>("[data-island]:not([data-island-mounted])")];
    if (elements.length === 0) return;

    const [{ createElement }, { createRoot }] = await Promise.all([import("react"), import("react-dom/client")]);

    await Promise.all(
        elements.map(async (element) => {
            const name = element.dataset.island;
            const load = islands[`../islands/${name}.tsx`];
            if (!load) {
                console.error(`Island "${name}" not found in frontend/src/islands/`);
                return;
            }

            element.dataset.islandMounted = "";
            try {
                const props = JSON.parse(element.dataset.props || "{}");
                const { default: Component } = await load();
                createRoot(element).render(createElement(Component, props));
            } catch (error) {
                console.error(`Island "${name}" failed to mount`, error);
            }
        }),
    );
}
