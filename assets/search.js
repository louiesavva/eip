/*
 * Transcript search for conversations.html.
 *
 * The page works without this script. With it, a search box appears that
 * loads data/search-index.json on first use and finds moments across the
 * episodes' captions, each linked to that point in the YouTube video.
 */
(function () {
  'use strict';

  const form = document.getElementById('search');
  if (!form || !window.fetch) return;

  const input = form.querySelector('input');
  const status = document.getElementById('search-status');
  const results = document.getElementById('search-results');
  const SHOWN_PER_EPISODE = 3;
  const MAX_PER_EPISODE = 40;
  const NEAR = 120;          // characters: how close words must be when not an exact phrase
  const SAME_MOMENT = 160;   // characters: hits closer than this count as one moment

  let items = null;
  let loading = null;
  let timer = null;

  form.hidden = false;

  function normalise(s) {
    return s.toLowerCase()
      .replace(/[‘’]/g, "'")
      .replace(/[^a-z0-9' ]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function load() {
    if (!loading) {
      status.textContent = 'Loading transcripts…';
      loading = fetch(form.dataset.index)
        .then(function (r) {
          if (!r.ok) throw new Error(r.status);
          return r.json();
        })
        .then(function (data) {
          items = data.items.map(function (it) {
            let text = '';
            let t = 0;
            const starts = [];
            const times = [];
            it.s.forEach(function (seg, i) {
              t += it.t[i];
              starts.push(text.length);
              times.push(t);
              text += seg + ' ';
            });
            return { n: it.n, id: it.id, title: it.title, text: text, starts: starts, times: times };
          });
          status.textContent = '';
        })
        .catch(function () {
          loading = null;
          status.textContent = 'Sorry, the transcripts could not be loaded. Please try again.';
        });
    }
    return loading;
  }

  // Every place `word` occurs at the start of a word in `text`, as [start, end].
  function occurrences(text, word) {
    const out = [];
    let i = text.indexOf(word);
    while (i !== -1) {
      if (i === 0 || text.charCodeAt(i - 1) === 32) out.push([i, i + word.length]);
      i = text.indexOf(word, i + 1);
    }
    return out;
  }

  // First occurrence in a sorted list that starts at or after `pos`.
  function firstFrom(list, pos) {
    let lo = 0;
    let hi = list.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (list[mid][0] < pos) lo = mid + 1; else hi = mid;
    }
    return lo;
  }

  // Places where all `words` occur within NEAR characters of each other.
  function nearby(text, words) {
    const lists = words.map(function (w) { return occurrences(text, w); })
      .sort(function (a, b) { return a.length - b.length; });
    if (lists.some(function (l) { return l.length === 0; })) return [];
    const anchor = lists[0];
    const rest = lists.slice(1);
    const hits = [];
    anchor.forEach(function (a) {
      let lo = a[0];
      let hi = a[1];
      for (const list of rest) {
        const k = firstFrom(list, a[0] - NEAR);
        if (k >= list.length || list[k][0] > a[0] + NEAR) return;
        lo = Math.min(lo, list[k][0]);
        hi = Math.max(hi, list[k][1]);
      }
      hits.push([lo, hi]);
    });
    return hits;
  }

  function timeAt(item, pos) {
    let lo = 0;
    let hi = item.starts.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (item.starts[mid] <= pos) lo = mid; else hi = mid - 1;
    }
    return item.times[lo];
  }

  function clock(sec) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = String(sec % 60).padStart(2, '0');
    return h ? h + ':' + String(m).padStart(2, '0') + ':' + s : m + ':' + s;
  }

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // A stretch of text around a hit, with the search terms marked.
  function snippet(text, hit, terms) {
    let a = Math.max(0, hit[0] - 90);
    let b = Math.min(text.length, hit[1] + 130);
    if (a > 0) a = text.indexOf(' ', a) + 1;
    if (b < text.length) b = text.lastIndexOf(' ', b);
    const piece = text.slice(a, b).trim();

    const marks = [];
    terms.forEach(function (term) {
      occurrences(piece, term).forEach(function (r) { marks.push(r); });
    });
    marks.sort(function (x, y) { return x[0] - y[0]; });

    let html = '';
    let at = 0;
    marks.forEach(function (r) {
      if (r[0] < at) return;
      html += escapeHtml(piece.slice(at, r[0])) + '<mark>' + escapeHtml(piece.slice(r[0], r[1])) + '</mark>';
      at = r[1];
    });
    html += escapeHtml(piece.slice(at));
    return (a > 0 ? '… ' : '') + html + (b < text.length ? ' …' : '');
  }

  function search(raw) {
    // Drop a trailing 's: matches are made at the start of words, so "god"
    // still finds "god's", and the captions often miss the possessive anyway.
    const query = normalise(raw.replace(/["“”]/g, ' ')).replace(/'s\b/g, '');
    if (query.length < 2) return null;
    const words = query.split(' ');

    function run(find) {
      const found = [];
      items.forEach(function (item) {
        const moments = [];
        let last = -Infinity;
        for (const hit of find(item.text)) {
          if (hit[0] - last < SAME_MOMENT) continue;
          last = hit[0];
          moments.push(hit);
          if (moments.length >= MAX_PER_EPISODE) break;
        }
        if (moments.length) found.push({ item: item, moments: moments });
      });
      return found;
    }

    let mode = 'phrase';
    let found = run(function (text) { return occurrences(text, query); });
    if (!found.length && words.length > 1) {
      mode = 'near';
      found = run(function (text) { return nearby(text, words); });
    }
    found.sort(function (x, y) {
      return y.moments.length - x.moments.length || x.item.n - y.item.n;
    });
    return { query: query, terms: mode === 'phrase' ? [query] : words, mode: mode, found: found };
  }

  function momentHtml(item, hit, terms) {
    const t = Math.max(0, timeAt(item, hit[0]) - 2);
    const url = 'https://www.youtube.com/watch?v=' + encodeURIComponent(item.id) + '&t=' + t + 's';
    return '<li><a class="ts" href="' + url + '">' + clock(t) + '</a> ' +
      '<span class="snip">' + snippet(item.text, hit, terms) + '</span></li>';
  }

  function render(res) {
    if (!res) {
      results.hidden = true;
      results.innerHTML = '';
      status.textContent = '';
      return;
    }
    const q = '“' + res.query + '”';
    if (!res.found.length) {
      results.hidden = true;
      results.innerHTML = '';
      status.textContent = 'Nothing found for ' + q + '. The captions are automatic, so a different spelling may work.';
      return;
    }
    const total = res.found.reduce(function (sum, f) { return sum + f.moments.length; }, 0);
    const eps = res.found.length;
    status.textContent =
      (res.mode === 'near' ? 'No exact matches for ' + q + ', but these words come up together ' : q + ' comes up ') +
      total + (total === 1 ? ' time' : ' times') + ' in ' + eps + (eps === 1 ? ' episode.' : ' episodes.');

    results.innerHTML = res.found.map(function (f) {
      const it = f.item;
      const shown = f.moments.slice(0, SHOWN_PER_EPISODE);
      const more = f.moments.slice(SHOWN_PER_EPISODE);
      const count = f.moments.length + (f.moments.length >= MAX_PER_EPISODE ? '+' : '');
      let html = '<li class="result"><h3><a href="#ep-' + it.n + '">#' + it.n + ' ' + escapeHtml(it.title) + '</a> ' +
        '<span class="ep-role">' + count + (f.moments.length === 1 ? ' moment' : ' moments') + '</span></h3>' +
        '<ul class="moments">' + shown.map(function (h) { return momentHtml(it, h, res.terms); }).join('') + '</ul>';
      if (more.length) {
        html += '<details><summary>' + more.length + ' more</summary><ul class="moments">' +
          more.map(function (h) { return momentHtml(it, h, res.terms); }).join('') + '</ul></details>';
      }
      return html + '</li>';
    }).join('');
    results.hidden = false;
  }

  function go(raw, push) {
    const url = new URL(window.location.href);
    if (normalise(raw)) url.searchParams.set('q', raw.trim()); else url.searchParams.delete('q');
    if (push) window.history.replaceState(null, '', url);
    return load().then(function () {
      if (items) render(search(raw));
    });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    clearTimeout(timer);
    go(input.value, true);
  });

  input.addEventListener('input', function () {
    clearTimeout(timer);
    const value = input.value;
    if (normalise(value).length < 3) {
      if (!normalise(value)) go('', true);
      return;
    }
    timer = setTimeout(function () { go(value, true); }, 300);
  });

  input.addEventListener('focus', load, { once: true });

  const initial = new URLSearchParams(window.location.search).get('q');
  if (initial) {
    input.value = initial;
    go(initial, false).then(function () {
      form.scrollIntoView({ block: 'start' });
    });
  }
})();
