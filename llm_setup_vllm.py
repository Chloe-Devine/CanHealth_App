import requests
import json

nonthinking_settings = {
    'max_tokens': 1024,
    'temperature':0.7,
    'top_k':20,
    'top_p':0.8,
    'min_p': 0.01,
    'repetition_penalty' :1.05
}

thinking_settings = {
    'max_tokens': 1024,
    'temperature':0.6,
    'top_k':20,
    'top_p':0.95,
    'min_p': 0.01,
    'repetition_penalty' :1.05
}


promptheader = '''<|im_start|>user\n'''
promptfooter = '''\n<|im_end|>\n<|im_start|>assistant\n<think>'''

def get_final_response(prompt, output):

    prompt = prompt + output + "\nConsidering the limited time by the user, I have to give the solution based on the thinking directly now.\n</think>.\n\n"

    thinking , content = llm_execute(prompt=prompt,enable_thinking=False)

    thinking_content = output + "\nConsidering the limited time by the user, I have to give the solution based on the thinking directly now.\n</think>.\n\n"

    return thinking_content.strip(), content

def llm_execute(prompt, max_tokens =512, settings=nonthinking_settings, enable_thinking = False,api_key=None):
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }

    prompt = promptheader + prompt + promptfooter
    if not enable_thinking:
        prompt += "\n\n</think>\n\n"



    url = "http://127.0.0.1:8001/v1/completions"
    data = {"prompt": prompt,
            "temperature": settings['temperature'],
            "max_tokens": settings['max_tokens'],
            "top_p": settings['top_p'],
            "top_k": settings['top_k'],
            "min_p": settings['min_p'],
            # "repetition_penalty": settings['repetition_penalty'],

            }

    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=600)
    response = response.json()
    print(response)

    if len(response["choices"]) == 1:
        output = response["choices"][0]["text"]
        if enable_thinking:
            if '</think>' not in output:
                thinking_content , content = get_final_response(prompt,output)
                return thinking_content, content
            else:
                thinking_content = output[:output.find('</think>')].strip()
                content = output[output.find('</think>')+8:].strip()
                return thinking_content, content
        else:
            return '', output.strip()

    else:
        output_list = []
        for reply in response["choices"]:
            output_list.append(reply["text"].strip())
        return output_list, 200
#


def llm_response(prompt ,settings=nonthinking_settings,api_key=None):
    messages = [
        {"role": "user", "content": prompt}
    ]
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }

    url =  "http://127.0.0.1:8001/v1/chat/completions"
    data = {"mode": "instruct",
            "messages": messages,
            "temperature": settings['temperature'],
            # "max_tokens": settings['max_tokens'],
            "top_p": settings['top_p'],
            "top_k": settings['top_k'],
            "min_p": settings['min_p'],
            "repetition_penalty": settings['repetition_penalty'],

            }
    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=300)
    response = response.json()
    #['choices'][0]['message']['content']

    return response

