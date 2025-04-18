import threading
import time

import customtkinter as ctk
import cv2

from utils.state import LiveState, State
from visual.preprocessing import ExtractPriority, FindVisualDifference, PreprocessFrame, ExtractPriorityOld

listPriorityKeys = ["low", "medium", "high"]

limit = 60


def CompareAction(
    old: cv2.typing.MatLike,
    new: cv2.typing.MatLike,
    threshold: int,
    action: callable,
):
    thread = threading.Thread(
        target=lambda: action(FindVisualDifference(old, new, threshold)),
        daemon=True,
    )
    thread.start()


state = State.get_instance()
def CompareNoise(
    capture: cv2.VideoCapture,
    liveState: LiveState,
    actions: dict[str, callable],
    # videoLabel: ctk.CTkLabel,
):
    oldFrame = None

    def createStopper(action):
        def actionWithStopper(value):
            action(value)
            if value >= limit:
                liveState["isComparing"] = False
                liveState["isDetecting"] = True
                liveState["isSaving"] = True

        return actionWithStopper

    while liveState["isComparing"]:
        ret1, frameNew = capture.read()
        if not ret1:
            capture.release()
            raise IOError("Failed to capture new frame")

        grayNew = PreprocessFrame(frameNew)

        copy, high = ExtractPriority(grayNew, state.data["priority"]["high"])
        low, medium = ExtractPriority(copy, state.data["priority"]["medium"])
        
        # copy, high = ExtractPriorityOld(grayNew, state.data["oldpriority"]["high"])
        # low, medium = ExtractPriorityOld(copy, state.data["oldpriority"]["medium"])

        newFrame = {
            "low": low,
            "medium": medium,
            "high": high,
        }

        if oldFrame is not None:
            [
                CompareAction(
                    oldFrame[key],
                    newFrame[key],
                    state.data["priorityThreshold"][key],
                    createStopper(actions[key]),
                )
                for key in listPriorityKeys
            ]

        time.sleep(state.data["interval"])
        oldFrame = newFrame
        
    liveState["isComparing"] = False
    liveState["isDetecting"] = True
    liveState["isSaving"] = True
