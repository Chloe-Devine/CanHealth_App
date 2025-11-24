print('loading utils')
import utils
from datetime import datetime
import ast


def process_request(exam_requested, indication, api_key):
    # get top n protocols
    n = 6
    topk_protocols, topk_definitions = utils.get_topk_definitions(indication,exam_requested,top_k=n)

    # get protocol prediction
    protocol_dict_defs = {k.strip():v.strip() for k,v in zip(topk_protocols,topk_definitions)}
    protocol_thinking, protocol_pred = utils.get_protocol(indication,exam_requested,protocol_dict_defs,api_key=api_key, max_tokens=1024, enable_thinking=True)

    priority_thinking, priority_pred = '', ''
    #get priority prediction
    protocol_pred = ast.literal_eval(protocol_pred)

    if not any(x in protocol_pred for x in ['Procedure','No appropriate protocol found']):
        priority_thinking, priority_pred = utils.get_priority(indication, exam_requested, protocol_pred,api_key=api_key, max_tokens=1024,enable_thinking=True)
        if 'Not in guidelines' in priority_pred:
            priority_thinking, priority_pred = utils.get_inferred_priority(indication, exam_requested, protocol_pred, api_key=api_key, max_tokens=1024,
                                                         enable_thinking=True)
        priority_pred = ast.literal_eval(priority_pred)

    else:
        if 'Procedure' in protocol_pred:
            priority_thinking, priority_pred = '', ['Procedure Protocol']
        elif 'No appropriate protocol found':
            priority_thinking, priority_pred = '', ['No Protocol Found']
        else:
            priority_thinking, priority_pred = '', []

    # Summarize Protocol
    print('JOINING:', ", ".join(protocol_pred))
    thinking, answer = utils.protocol_summary(pred=", ".join(protocol_pred), reasoning=protocol_thinking)
    protocol_summary = answer

    # Summarize Priority
    print('PRIORITY:',priority_pred[0])
    thinking, answer = utils.priority_summary(pred=priority_pred[0], reasoning=priority_thinking)
    priority_summary = answer

    output = {'protocol_thinking': protocol_summary, 'protocol_prediction': protocol_pred,
              'priority_thinking': priority_summary, 'priority_prediction': priority_pred}

    return output

def dict_to_markdown(data: dict) -> str:
    """
    Convert a dict -> markdown string.
    - Keys become level-4 headings (#### **key**)
    - Lists become comma-separated strings
    - Nested dicts are rendered recursively
    - Multiline strings are preserved
    """
    def _format_value(v):
        if isinstance(v, dict):
            return dict_to_markdown(v)
        if isinstance(v,list):
            # Convert list to comma-separated string
            return ", ".join(str(item) for item in v)
        # for strings / numbers: preserve newlines in strings
        return str(v)

    md_parts = []
    for key, val in data.items():
        key = key.replace('_', ' ').title()
        md_parts.append(f"#### **{key}**\n")
        md_parts.append(_format_value(val))
        md_parts.append("")  # blank line for spacing

    return "\n".join(md_parts)


