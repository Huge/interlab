import { useState } from "react";
import { Context, gatherKindsAndTags } from "../model/Context";
import { OpenerMode } from "./DataBrowser";
import { ContextView } from "./ContextView";

const config = { themeWithBoxes: false };

export function SingleContextScreen(props: { context: Context }) {
    const [opened, setOpened] = useState<Set<string>>(() => {
        const s = new Set<string>();
        gatherKindsAndTags(props.context, s);
        s.add(props.context.uid)
        return s
    });

    /* Copy pasted from DataBrowser, need some refactoring */
    function setOpen(keys: string | string[], mode: OpenerMode) {
        setOpened((op) => {
            const o = new Set(op);
            if (!Array.isArray(keys)) {
                keys = [keys]
            }
            if (mode === OpenerMode.Toggle) {
                for (const key of keys) {
                    if (!o.delete(key)) {
                        o.add(key)
                    }
                }
            } else if (mode === OpenerMode.Open) {
                for (const key of keys) {
                    o.add(key)
                }
            } else {
                for (const key of keys) {
                    o.delete(key)
                }
            }
            return o;
        })
    }

    return <ContextView context={props.context} opened={opened} setOpen={setOpen} config={config} />
}