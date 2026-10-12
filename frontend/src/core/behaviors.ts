export type Behavior = (element: HTMLElement) => void;

// Eager: behaviors are tiny and must work right after page load without extra requests
const behaviors = import.meta.glob<Behavior>("../behaviors/*.ts", { eager: true, import: "default" });

export function attachBehaviors(root: ParentNode = document) {
    root.querySelectorAll<HTMLElement>("[data-behavior]").forEach((element) => {
        const attached = new Set((element.dataset.behaviorAttached || "").split(" ").filter(Boolean));

        for (const name of (element.dataset.behavior || "").split(" ").filter(Boolean)) {
            if (attached.has(name)) continue;

            const behavior = behaviors[`../behaviors/${name}.ts`];
            if (!behavior) {
                console.error(`Behavior "${name}" not found in frontend/src/behaviors/`);
                continue;
            }

            try {
                behavior(element);
                attached.add(name);
            } catch (error) {
                console.error(`Behavior "${name}" failed`, error);
            }
        }

        element.dataset.behaviorAttached = [...attached].join(" ");
    });
}
