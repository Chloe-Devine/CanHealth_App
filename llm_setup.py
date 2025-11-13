print('importing llm script')
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

model_name = "../../text-generation-webui-main/user_data/models/Qwen_Qwen3-14B"
print('loading model')
# load the tokenizer and the model
tokenizer = AutoTokenizer.from_pretrained(model_name)

bnb_config = BitsAndBytesConfig(
    load_in_8bit=True,
    llm_int8_enable_fp32_cpu_offload=True  # allow spillover
)
# bnb_config = BitsAndBytesConfig(
#     load_in_4bit=True,
#     bnb_4bit_quant_type="nf4",        # NF4 is usually best
#     bnb_4bit_use_double_quant=True,   # nested quantization for efficiency
#     bnb_4bit_compute_dtype="bfloat16" # use torch.float16 if your GPU doesn't support bf16
# )

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
#     load_in_8bit = True,
    quantization_config=bnb_config,
    device_map="auto"
)
print('model loaded')
nonthinking_settings = {
    'temperature':0.7,
    'top_k':20,
    'top_p':0.8,
    }

thinking_settings = {
    'temperature':0.6,
    'top_k':20,
    'top_p':0.95,
}
#prompt, api_key=None, settings=nonthinking_settings, enable_thinking=False, poll_interval=2

def llm_execute(prompt, max_tokens=8192, enable_thinking=True, system_prompt=None):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})
    if enable_thinking:
        settings = thinking_settings
    else:
        settings = nonthinking_settings

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking  # Switches between thinking and non-thinking modes. Default is True.
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)


    # input_ids = model_inputs.input_ids[0]  # shape: [seq_len]
    # num_input_tokens = model_inputs.input_ids.shape[1]
    # print(f"Model input tokens: {num_input_tokens}")
    #
    # # Detokenize back to string
    # detokenized_prompt = tokenizer.decode(input_ids, skip_special_tokens=False)
    #
    # # Save to a file
    # with open("data/debug_prompt.txt", "a", encoding="utf-8") as f:
    #     f.write(detokenized_prompt+'\n\n'+ '---------------------------------------------------------------')



    # conduct text completion

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=max_tokens,
        temperature=settings['temperature'],
        top_p=settings['top_p'],
        top_k=settings['top_k']
    )

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
    output = tokenizer.decode(output_ids, skip_special_tokens=True)

    messages = []
    rerun = False
    if '</think>' not in output and enable_thinking:
        rerun = True
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        prompt = prompt + output + "\nConsidering the limited time by the user, I have to give the solution based on the thinking directly now.\n</think>.\n\n"

        messages.append({"role": "user", "content": prompt})

        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False)

        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

        # conduct text completion
        settings = nonthinking_settings

        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_tokens,
            temperature=settings['temperature'],
            top_p=settings['top_p'],
            top_k=settings['top_k'])

        output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()

        # parsing thinking content
    try:
        # rindex finding 151668 (</think>)
        index = len(output_ids) - output_ids[::-1].index(151668)
    except ValueError:
        index = 0

    thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
    content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")
    if rerun:
        thinking_content = output + "\nConsidering the limited time by the user, I have to give the solution based on the thinking directly now.\n</think>.\n\n"
        content = tokenizer.decode(output_ids, skip_special_tokens=True).strip()

    return thinking_content, content

