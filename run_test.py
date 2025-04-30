import threading
from vis_main import vis_main
from ir_main import ir_main

if __name__ == "__main__":
    vis_thread = threading.Thread(target=vis_main, args=("d:/test/test.mp4", "0.0.0.0", 8081))
    ir_thread = threading.Thread(target=ir_main, args=("d:/test/test1.mp4", "0.0.0.0", 8082))

    vis_thread.start()
    ir_thread.start()

    vis_thread.join()
    ir_thread.join()

    print("Both vis_main and ir_main have completed.")