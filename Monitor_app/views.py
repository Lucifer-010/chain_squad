from django.shortcuts import render
from . import tasks

# Create your views here.

def home(request):
    rpc_to_use = tasks.RPC_URL  # Default RPC

    if request.method == 'POST':
        # If the form is submitted, use the provided RPC URL
        rpc_to_use = request.POST.get('rpc_url', tasks.RPC_URL).strip()

    # Fetch data from your tasks using the determined RPC URL
    context = tasks.get_l3_vital_health(rpc_to_use)
    return render(request, "index.html", context)