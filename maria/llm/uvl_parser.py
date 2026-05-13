import re
import textwrap

VALID_STAGES = {'empatizar', 'definir', 'idear', 'prototipar', 'testear', ''}
VALID_Q_TYPES = {'text', 'textarea', 'number', 'select'}


class UVLParseError(Exception):
    pass


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def parse_technique_uvl(content: str) -> dict:
    """
    Parse a technique UVL file and return a dict ready for Technique.objects.create().

    Mandatory fields: id, name, stage
    Optional fields:  icon, inputs_description, outputs_description, prompt (inline or triple-quoted)
    Questionnaire:    zero or more Question blocks with id, label, type, placeholder/options
    """
    result = {
        'tech_id': '',
        'name': '',
        'stage': '',
        'icon': '⚙️',
        'inputs_description': '',
        'outputs_description': '',
        'default_prompt': '',
        'questionnaire': [],
    }

    # Namespace → fallback tech_id
    ns = re.search(r'^namespace\s+(\S+)', content, re.MULTILINE)
    if ns:
        result['tech_id'] = re.sub(r'[^a-z0-9]+', '_', ns.group(1).lower()).strip('_')

    # Extract triple-quoted prompt first (may contain any characters)
    tq = re.search(r'prompt\s+"""(.*?)"""', content, re.DOTALL)
    if tq:
        result['default_prompt'] = textwrap.dedent(tq.group(1)).strip()
        content = content[:tq.start()] + content[tq.end():]

    # Strip comments and blank lines, build token list
    lines = [l for l in content.splitlines()
             if l.strip() and not l.strip().startswith('//')]

    in_questionnaire = False
    current_q: dict | None = None

    attr_re = re.compile(r'^(\w+)\s+"([^"]*)"$')

    for line in lines:
        s = line.strip()

        if s in ('features', 'Technique', 'mandatory', 'optional', 'or',
                 'alternative', 'constraints', 'namespace'):
            continue
        if s.startswith('namespace '):
            continue

        if s == 'Questionnaire':
            in_questionnaire = True
            if current_q is not None:
                result['questionnaire'].append(current_q)
                current_q = None
            continue

        if s == 'Question':
            if current_q is not None:
                result['questionnaire'].append(current_q)
            current_q = {}
            continue

        m = attr_re.match(s)
        if not m:
            continue
        key, val = m.group(1), m.group(2)

        if in_questionnaire and current_q is not None:
            if key == 'id':
                current_q['id'] = val
            elif key == 'label':
                current_q['label'] = val
            elif key == 'type':
                current_q['type'] = val
            elif key == 'placeholder':
                current_q['placeholder'] = val
            elif key == 'options':
                current_q['options'] = [o.strip() for o in val.split(',') if o.strip()]
        else:
            if key == 'id':
                result['tech_id'] = val
            elif key == 'name':
                result['name'] = val
            elif key == 'stage':
                result['stage'] = val
            elif key == 'icon':
                result['icon'] = val
            elif key == 'inputs_description':
                result['inputs_description'] = val
            elif key == 'outputs_description':
                result['outputs_description'] = val
            elif key == 'prompt':
                result['default_prompt'] = val

    if current_q is not None:
        result['questionnaire'].append(current_q)

    # ── Validation ──────────────────────────────────────────────────────────
    if not result['tech_id']:
        raise UVLParseError("Campo obligatorio 'id' no encontrado.")
    if not result['name']:
        raise UVLParseError("Campo obligatorio 'name' no encontrado.")
    if result['stage'] not in VALID_STAGES:
        raise UVLParseError(
            f"Stage inválido: '{result['stage']}'. "
            f"Válidos: {sorted(s for s in VALID_STAGES if s)}"
        )
    for q in result['questionnaire']:
        missing = [f for f in ('id', 'label', 'type') if not q.get(f)]
        if missing:
            raise UVLParseError(f"Pregunta incompleta, faltan campos {missing}: {q}")
        if q['type'] not in VALID_Q_TYPES:
            raise UVLParseError(
                f"Tipo de pregunta inválido: '{q['type']}'. Válidos: {sorted(VALID_Q_TYPES)}"
            )
        if q['type'] == 'select' and not q.get('options'):
            raise UVLParseError(f"Pregunta select '{q['id']}' requiere campo 'options'.")

    return result
