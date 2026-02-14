// PostCSS config for Tailwind CSS processing
// Scopes all Tailwind output under .messaging-chat-root to avoid polluting Frappe desk styles
import tailwindcss from "tailwindcss";
import tailwindcssNesting from "@tailwindcss/nesting";
import postcssPrefixSelector from "postcss-prefix-selector";
import autoprefixer from "autoprefixer";
import cssnano from "cssnano";

export default {
  plugins: [
    tailwindcssNesting,
    tailwindcss,
    autoprefixer,
    postcssPrefixSelector({
      prefix: ".messaging-chat-root",
      transform: function (prefix, selector, prefixedSelector) {
        // Don't prefix selectors for popovers/dropdowns that render outside the root
        if (
          selector.startsWith("#frappeui-popper-root") ||
          selector.startsWith("[data-tippy-root]") ||
          selector.includes("[data-headlessui-") ||
          selector.includes("[data-reka-")
        ) {
          return selector;
        }

        // Popover content also needs to match without the prefix
        const popoverSelectors = [
          "#frappeui-popper-root " + selector,
          "[data-tippy-root] " + selector,
          "[data-reka-popper-content-wrapper] " + selector,
        ];

        return [prefix + " " + selector, ...popoverSelectors].join(", ");
      },
    }),
    cssnano,
  ],
};
