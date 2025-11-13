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

    print('thinking:',protocol_thinking)
    print('answer:',protocol_pred)
    priority_thinking, priority_pred = '', ''
    #get priority prediction

    if not any(x in protocol_pred for x in ['Procedure','No appropriate protocol found']):
        priority_thinking, priority_pred = utils.get_priority(indication, exam_requested, protocol_pred,api_key=api_key, max_tokens=1024,enable_thinking=True)
        if priority_pred == 'Not in guidelines':
            priority_thinking, priority_pred = utils.get_inferred_priority(indication, exam_requested, protocol_pred, api_key=api_key, max_tokens=1024,
                                                         enable_thinking=True)

    else:
        if 'Procedure' in protocol_pred:
            priority_thinking, priority_pred = '', 'Procedure Protocol'
        elif 'No appropriate protocol found':
            priority_thinking, priority_pred = '', 'No Protocol Found'
        else:
            priority_thinking, priority_pred = '', ''

    output = {'protocol_thinking': protocol_thinking, 'protocol_pred': protocol_pred,
              'priority_thinking': priority_thinking, 'priority_thinking': priority_pred}

    print('thinking:', priority_thinking)
    print('answer:', priority_pred)


    return output


def dict_to_markdown(data: dict) -> str:
    md = []
    for key, value in data.items():
        md.append(f"#### **{key}**\n")
        md.append(str(value))
    return "\n".join(md)