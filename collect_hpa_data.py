import subprocess
import time
import matplotlib.pyplot as plt
from collections import defaultdict
import argparse
import json

# Function to get the current HPA status
def get_hpa_metrics():
    try:
        # Run 'kubectl get hpa' command
        output = subprocess.check_output(["kubectl", "get", "hpa", "-o", "custom-columns=NAME:.metadata.name,CURRENT:.status.currentReplicas,CPU:.status.currentMetrics[0].resource.current.averageUtilization"], text=True)
        # Parse the output
        lines = output.strip().split("\n")[1:]  # Skip the header
        metrics = {}
        for line in lines:
            parts = line.split()
            hpa_name = parts[0]
            current_replicas = int(parts[1])
            cpu_utilization = int(parts[2]) if len(parts) > 2 else None  # Handle case where CPU data might be missing
            metrics[hpa_name] = {'replicas': current_replicas, 'cpu': cpu_utilization}
        return metrics
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return {}

def convert_to_seconds(time_str):
    if time_str[-1] == 's':
        return int(time_str[:-1])
    elif time_str[-1] == 'm':
        return int(time_str[:-1]) * 60
    elif time_str[-1] == 'h':
        return int(time_str[:-1]) * 3600
    else:
        return int(time_str)

def output_plot(args, graph_name):
    if args.save:
        plt.savefig(f"{args.output}_{graph_name}.png")
    else:
        plt.show()

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Monitor HPA metrics.')
    parser.add_argument('--interval', type=str, default="1s", help='Interval in seconds between each kubectl get hpa command.')
    parser.add_argument('--total_time', type=str, default="1m", help='total time in seconds to monitor the HPA metrics.')
    parser.add_argument('--more_time', type=str, default="0s", help='Extra time in seconds to monitor the HPA metrics.')
    parser.add_argument('--output', type=str, default='hpa_metrics', help='Output file to save the plot.')
    parser.add_argument('--save', action='store_true', help='Save the plot to a file.')
    parser.add_argument('--save_interval', type=str, default="", help='Save the plot every interval.')
    parser.add_argument('--timestemp', action='store_true', help='Add a timestamp to the output file.')
    parser.add_argument('--from_file', type=str, help='Load the HPA metrics from a file.')
    parser.add_argument('--graph_metrics', type=str, default='same', help='Type of graph to draw. Options: separate, together, all')
    parser.add_argument('--graph_services', type=str, default='together', help='Type of graph to draw. Options: separate, together, all')
    args = parser.parse_args()

    # Convert interval and total_time to seconds
    args.interval = convert_to_seconds(args.interval)
    args.total_time = convert_to_seconds(args.total_time) + convert_to_seconds(args.more_time)
    args.save_interval = convert_to_seconds(args.save_interval) if args.save_interval else None

    # Store data over time
    time_intervals = []
    replica_data = defaultdict(list)
    cpu_data = defaultdict(list)

    # Run the monitoring loop
    start_time = time.time()
    previous_time = start_time

    if args.timestemp:
            # add the start time in format YYYY-MM-DD_HH-MM-SS
            args.output += '_' + time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(start_time))

    if args.from_file:
        with open(args.from_file, 'r') as f:
            data = json.load(f)
            time_intervals = data['time']
            replica_data = data['replicas']
            cpu_data = data['cpu']
    else:
        try:
            if args.save_interval:
                with open("online_metrics.json", 'w') as f:
                    f.write("{")
            previous_time_for_save = start_time
            info_since_last_save = {}
            while time.time() - start_time < args.total_time:
                current_time = time.time()
                time_intervals.append(current_time)
                hpa_metrics = get_hpa_metrics()
                
                for hpa_name, metric in hpa_metrics.items():
                    replica_data[hpa_name].append(metric['replicas'])
                    cpu_data[hpa_name].append(metric['cpu'])
                
                if args.save_interval:
                    info_since_last_save[int(current_time)] = hpa_metrics
                    if current_time - previous_time_for_save >= args.save_interval:
                        with open("online_metrics.json", 'a') as f:
                            print("Saving data")
                            f.write("," + json.dumps(info_since_last_save)[1:-1])
                        previous_time_for_save = current_time
                        info_since_last_save = {}

                # Sleep for the remaining time
                time_to_sleep = previous_time + args.interval - time.time()
                if time_to_sleep > 0:
                    time.sleep(time_to_sleep)
                previous_time = time.time()

        except KeyboardInterrupt:
            pass

        print("Monitoring stopped.")
    
    if args.save:
        with open(args.output + '.json', 'w') as f:
            json.dump({'time': time_intervals, 'replicas': replica_data, 'cpu': cpu_data}, f)

    if args.save_interval:
        with open("online_metrics.json", 'a') as f:
            f.write("}")


    if (args.graph_metrics == 'together' or args.graph_metrics == 'all') and (args.graph_services == 'together' or args.graph_services == 'all'):
        # Plot the results
        fig, ax1 = plt.subplots()

        ax2 = ax1.twinx()
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Number of Replicas', color='tab:blue')
        ax2.set_ylabel('CPU Utilization (%)', color='tab:red')

        for hpa_name, replicas in replica_data.items():
            ax1.plot(time_intervals[:len(replicas)], replicas, label=f'{hpa_name} Replicas', color='tab:blue')
        
        for hpa_name, cpu in cpu_data.items():
            ax2.plot(time_intervals[:len(cpu)], cpu, label=f'{hpa_name} CPU', color='tab:red', linestyle='--')
        
        ax1.tick_params(axis='y', labelcolor='tab:blue')
        ax2.tick_params(axis='y', labelcolor='tab:red')

        fig.tight_layout()
        plt.title('HPA Metrics Over Time')
        fig.legend(loc="upper left", bbox_to_anchor=(0,1), bbox_transform=ax1.transAxes)
        output_plot(args, graph_name='both_metrics')
    
    if (args.graph_metrics == 'together' or args.graph_metrics == 'all') and (args.graph_services == 'seperate' or args.graph_services == 'all'):
        for hpa_name, replicas in replica_data.items():
            fig, ax1 = plt.subplots()

            ax2 = ax1.twinx()
            ax1.set_xlabel('Time (s)')
            ax1.set_ylabel('Number of Replicas', color='tab:blue')
            ax2.set_ylabel('CPU Utilization (%)', color='tab:red')

            ax1.plot(time_intervals[:len(replicas)], replicas, label=f'{hpa_name} Replicas', color='tab:blue')
            ax2.plot(time_intervals[:len(cpu_data[hpa_name])], cpu_data[hpa_name], label=f'{hpa_name} CPU', color='tab:red', linestyle='--')

            ax1.tick_params(axis='y', labelcolor='tab:blue')
            ax2.tick_params(axis='y', labelcolor='tab:red')

            fig.tight_layout()
            plt.title(f'{hpa_name} Metrics Over Time')
            fig.legend(loc="upper left", bbox_to_anchor=(0,1), bbox_transform=ax1.transAxes)
            output_plot(args, graph_name=f"{hpa_name}_both_metrics")

    if (args.graph_metrics == 'seperate' or args.graph_metrics == 'all') and (args.graph_services == 'together' or args.graph_services == 'all'):
        plt.xlabel('Time (s)')
        plt.ylabel('Number of Replicas')
        plt.title('Replicas Over Time')
        for hpa_name, replicas in replica_data.items():
            plt.plot(time_intervals[:len(replicas)], replicas, label=f'{hpa_name} Replicas')
        plt.legend()
        output_plot(args, graph_name='replicas')

        plt.xlabel('Time (s)')
        plt.ylabel('CPU Utilization (%)')
        plt.title('CPU Over Time')
        for hpa_name, cpu in cpu_data.items():
            plt.plot(time_intervals[:len(cpu)], cpu, label=f'{hpa_name} CPU')
        plt.legend()
        output_plot(args, graph_name='cpu')

    if (args.graph_metrics == 'seperate' or args.graph_metrics == 'all') and (args.graph_services == 'seperate' or args.graph_services == 'all'):
        for hpa_name, replicas in replica_data.items():
            plt.xlabel('Time (s)')
            plt.ylabel('Number of Replicas')
            plt.title(f'{hpa_name} Replicas Over Time')
            plt.plot(time_intervals[:len(replicas)], replicas)
            output_plot(args, graph_name=f"{hpa_name}_replicas")

            plt.xlabel('Time (s)')
            plt.ylabel('CPU Utilization (%)')
            plt.title(f'{hpa_name} CPU Over Time')
            plt.plot(time_intervals[:len(cpu_data[hpa_name])], cpu_data[hpa_name])
            output_plot(args, graph_name=f"{hpa_name}_cpu")

if __name__ == "__main__":
    main()
