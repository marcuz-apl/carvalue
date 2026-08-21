#!/usr/bin/env bash
set -eu

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

version_file="$repo_root/VERSION"

fail() {
    printf 'versioning: %s\n' "$1" >&2
    exit 1
}

load_version() {
    [[ -f "$version_file" ]] || fail "VERSION file is missing"
    raw_version=$(cat "$version_file")
    raw_version=${raw_version//$'\r'/}

    if [[ "$raw_version" =~ ^v?([0-9]+)\.([0-9])\.([0-9])-([0-9]{6})([0-9a-z])$ ]]; then
        major=${BASH_REMATCH[1]}
        minor=${BASH_REMATCH[2]}
        patch=${BASH_REMATCH[3]}
        build_date=${BASH_REMATCH[4]}
        build_counter=${BASH_REMATCH[5]}
    else
        fail "malformed VERSION identifier: $raw_version"
    fi

    if [[ "$build_counter" == 0 ]]; then
        fail "build counter must start at 1"
    fi

    parsed_date=$(date -u -d "20${build_date}" +%y%m%d 2>/dev/null) || \
        fail "invalid calendar date in VERSION: $build_date"
    [[ "$parsed_date" == "$build_date" ]] || \
        fail "invalid calendar date in VERSION: $build_date"

    current_date=$(date -u +%y%m%d)
    [[ "$build_date" > "$current_date" ]] && \
        fail "future-dated VERSION identifier: $build_date"

    if [[ "$raw_version" == v* ]]; then
        normalized_version="$raw_version"
        is_legacy=0
    else
        normalized_version="v$raw_version"
        is_legacy=1
    fi
}

write_version() {
    printf '%s\n' "$1" > "$version_file"
}

next_patch_version() {
    next_major=$major
    next_minor=$minor
    next_patch=$patch
    if (( next_patch < 9 )); then
        next_patch=$((next_patch + 1))
    elif (( next_minor < 9 )); then
        next_patch=0
        next_minor=$((next_minor + 1))
    else
        next_patch=0
        next_minor=0
        next_major=$((next_major + 1))
    fi
}

next_build_counter() {
    if [[ "$build_date" != "$current_date" ]]; then
        next_counter=1
        return
    fi

    case "$build_counter" in
        1) next_counter=2 ;;
        2) next_counter=3 ;;
        3) next_counter=4 ;;
        4) next_counter=5 ;;
        5) next_counter=6 ;;
        6) next_counter=7 ;;
        7) next_counter=8 ;;
        8) next_counter=9 ;;
        9) next_counter=a ;;
        a) next_counter=b ;;
        b) next_counter=c ;;
        c) next_counter=d ;;
        d) next_counter=e ;;
        e) next_counter=f ;;
        f) next_counter=g ;;
        g) next_counter=h ;;
        h) next_counter=i ;;
        i) next_counter=j ;;
        j) next_counter=k ;;
        k) next_counter=l ;;
        l) next_counter=m ;;
        m) next_counter=n ;;
        n) next_counter=o ;;
        o) next_counter=p ;;
        p) next_counter=q ;;
        q) next_counter=r ;;
        r) next_counter=s ;;
        s) next_counter=t ;;
        t) next_counter=u ;;
        u) next_counter=v ;;
        v) next_counter=w ;;
        w) next_counter=x ;;
        x) next_counter=y ;;
        y) next_counter=z ;;
        z) fail "daily build counter exhausted for $current_date" ;;
        *) fail "invalid build counter: $build_counter" ;;
    esac
}

bump() {
    load_version
    (( is_legacy == 0 )) || fail "legacy VERSION requires: bash .githooks/versioning.sh normalize"
    next_patch_version
    next_build_counter
    next_version="v${next_major}.${next_minor}.${next_patch}-${current_date}${next_counter}"
    write_version "$next_version"
    git add -- VERSION
    printf '%s\n' "$next_version"
}

normalize() {
    load_version
    if (( is_legacy == 1 )); then
        write_version "$normalized_version"
        git add -- VERSION
    fi
    printf '%s\n' "$normalized_version"
}

stamp_message() {
    [[ $# -ge 1 ]] || fail "prepare-commit-msg requires a message file"
    message_file=$1
    load_version
    identifier="$normalized_version"
    temp_file=$(mktemp "${TMPDIR:-/tmp}/carvalue-commit-msg.XXXXXX")
    cleanup() {
        rm -f "$temp_file"
    }
    trap cleanup EXIT HUP INT TERM

    stamped=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        if (( stamped == 0 )) && [[ -n "$line" && "$line" != \#* ]]; then
            case "$line" in
                "$identifier"\ *)
                    line=${line#"$identifier" }
                    ;;
            esac
            printf '%s %s\n' "$identifier" "$line" >> "$temp_file"
            stamped=1
        else
            printf '%s\n' "$line" >> "$temp_file"
        fi
    done < "$message_file"
    mv "$temp_file" "$message_file"
    trap - EXIT HUP INT TERM
}

case "${1:-}" in
    bump)
        bump
        ;;
    normalize)
        normalize
        ;;
    stamp)
        shift
        stamp_message "$@"
        ;;
    *)
        fail "usage: $0 {bump|normalize|stamp MESSAGE_FILE}"
        ;;
esac
