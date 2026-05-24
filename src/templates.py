import re
from collections import defaultdict

RE_NUMBER = re.compile(r'^\d+$')
RE_HEX = re.compile(r'^0x[0-9a-fA-F]+$')
RE_IP = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
RE_PATH = re.compile(r'^[/\\]')
RE_UUID = re.compile(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
)
RE_TIMESTAMP_EMBEDDED = re.compile(r'\d{4}/\d{1,2}/\d{1,2}:\d{2}:\d{2}:\d{2}')
RE_EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
RE_HOSTNAME = re.compile(
    r'^[\w-]+\.\w{2,}$'
)

def tokenize(message):
    m = RE_TIMESTAMP_EMBEDDED.sub(' <*> ', message)
    return m.split()

def is_variable(token):
    if not token:
        return True
    if token.startswith('<') and token.endswith('>'):
        return True
    if RE_NUMBER.match(token):
        return True
    if RE_HEX.match(token):
        return True
    if RE_IP.match(token):
        return True
    if RE_PATH.match(token):
        return True
    if RE_UUID.match(token):
        return True
    if RE_EMAIL.match(token):
        return True
    if RE_HOSTNAME.match(token):
        return True
    if token.startswith('@'):
        return True
    if len(token) >= 40 and all(c in '0123456789abcdefABCDEF' for c in token):
        return True
    return False

def generate_template(tokens):
    return ' '.join('<*>' if is_variable(t) else t for t in tokens)

def extract_templates_sequential(messages):
    template_to_ids = {}
    templates = []
    template_ids = []
    next_id = 1
    for msg in messages:
        tokens = tokenize(str(msg))
        if not tokens:
            template_ids.append(0)
            templates.append('')
            continue
        template_str = generate_template(tokens)
        if template_str not in template_to_ids:
            template_to_ids[template_str] = next_id
            next_id += 1
        tid = template_to_ids[template_str]
        template_ids.append(tid)
        templates.append(template_str)
    return template_ids, templates

class LogCluster:
    def __init__(self, tid, template_tokens, msg):
        self.tid = tid
        self.template_tokens = template_tokens
        self.template_str = ' '.join(template_tokens)
        self.messages = [msg]
        self.count = 1

    def update(self, tokens, msg):
        self.template_tokens = self._merge(self.template_tokens, tokens)
        self.template_str = ' '.join(self.template_tokens)
        self.messages.append(msg)
        self.count += 1

    @staticmethod
    def _merge(t1, t2):
        merged = []
        for a, b in zip(t1, t2):
            if a == b:
                merged.append(a)
            else:
                merged.append('<*>')
        if len(t1) > len(t2):
            merged.extend(t1[len(t2):])
        elif len(t2) > len(t1):
            merged.extend('<*>' for _ in range(len(t2) - len(t1)))
        return merged

def extract_templates_drain(messages, depth=3, sim_threshold=0.8):
    tree = defaultdict(list)
    clusters = []
    template_ids = []
    templates_out = []
    tid_counter = 1

    for msg in messages:
        tokens = tokenize(str(msg))
        if not tokens:
            template_ids.append(0)
            templates_out.append('')
            continue

        token_len = len(tokens)
        cluster = None

        candidates = tree.get(token_len, [])

        for c in candidates:
            merged = LogCluster._merge(c.template_tokens, tokens)
            diff = sum(1 for a, b in zip(merged, tokens) if a == '<*>')
            total = max(len(merged), len(tokens))
            if total == 0:
                sim = 1.0
            else:
                sim = 1.0 - (diff / total)
            if sim >= sim_threshold:
                cluster = c
                break

        if cluster:
            cluster.update(tokens, msg)
            tid = cluster.tid
            template_str = cluster.template_str
        else:
            tid = tid_counter
            tid_counter += 1
            new_cluster = LogCluster(tid, tokens, msg)
            clusters.append(new_cluster)
            tree[token_len].append(new_cluster)
            template_str = new_cluster.template_str

        template_ids.append(tid)
        templates_out.append(template_str)

    return template_ids, templates_out, clusters
