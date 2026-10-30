# vue-advanced-chat (vendored source)

This directory is a copy of the `src/` tree and the `LICENSE` of
[advanced-chat/vue-advanced-chat](https://github.com/advanced-chat/vue-advanced-chat) at tag `2.1.2`
(commit `612668a91bbcb31b07c18b880755a2c5e03ea322`), unmodified. It is MIT-licensed; see `LICENSE`.

The chat view imports the Vue single-file components and the SCSS directly (Vite's `@vendor-chat` alias in
`vite.config.ts`), so it can mount `ChatWindow.vue` inside its own Vue app. The npm package ships only the
compiled web component in `dist/`, not this source.

The source is committed rather than a git submodule so that every checkout builds: a plain `git clone` and
`bench get-app` do not fetch submodules, and neither does a Nix flake's source tree or the CI checkout.

The files are excluded from formatting and linting (`generated` in `pyproject.toml`), so they stay
byte-identical to upstream. To move to another upstream release, replace `src/` and `LICENSE` with that
release's copies and update the tag and commit above:

```sh
git clone --depth 1 --branch <tag> https://github.com/advanced-chat/vue-advanced-chat.git /tmp/vac
rm -rf vendor/vue-advanced-chat/src && cp -r /tmp/vac/src /tmp/vac/LICENSE vendor/vue-advanced-chat/
```
