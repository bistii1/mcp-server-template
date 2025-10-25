import requests, json, time

API_KEY = 'pk_YOi0oF5NODiygbUzBi4MJ4taSmQwjPjfXuwNJN0YtGo'
WEBHOOK = 'https://poke.com/api/v1/inbound-sms/webhook'

def send(msg: str):
    r = requests.post(
        WEBHOOK,
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        },
        json={'message': msg}
    )
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.status_code, r.text)

tests = [
    # 1) create_user
    'Tell the subagent to use the "goalapp" integration\'s "create_user" tool with args {"username":"bisti","email":"bisti@example.com","learning_style":"visual"} and return the raw JSON.',
    # 2) update_user (adjust user_id after the first call if needed)
    'Tell the subagent to use the "goalapp" integration\'s "update_user" tool with args {"user_id":1,"learning_style":"auditory"} and return the raw JSON.',
    # 3) create_goal
    'Tell the subagent to use the "goalapp" integration\'s "create_goal" tool with args {"user_id":1,"skill_name":"Learn Python","timeline":30,"roadmap":[{"title":"Setup","description":"Install Python and VS Code"},{"title":"Basics","description":"Variables, loops, functions"},{"title":"Projects","description":"Build 2 small scripts"}],"coach_notes":{"tone":"encouraging","checkins_per_week":2}} and return the raw JSON.',
    # 4) get_context
    'Tell the subagent to use the "goalapp" integration\'s "get_context" tool with args {"goal_id":1} and return the raw JSON.',
    # 5) update_goal
    'Tell the subagent to use the "goalapp" integration\'s "update_goal" tool with args {"goal_id":1,"timeline":45,"coach_notes":{"tone":"concise","resources":["https://docs.python.org/3/tutorial/"]}} and return the raw JSON.',
    # 6) create_task
    'Tell the subagent to use the "goalapp" integration\'s "create_task" tool with args {"goal_id":1,"task_title":"Finish loops lesson","task_description":"Read chapter on for/while; do 5 exercises"} and return the raw JSON.',
    # 7) update_milestone (replace 3 with a real milestone_id from context)
    'Tell the subagent to use the "goalapp" integration\'s "update_milestone" tool with args {"milestone_id":3,"is_complete":true} and return the raw JSON.'
]

for t in tests:
    send(t)
    time.sleep(0.4)
