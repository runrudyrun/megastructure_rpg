"""Quest management system."""
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field

class QuestStatus(Enum):
    """Quest status states."""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()

class QuestType(Enum):
    """Types of quests."""
    MAIN = auto()
    SIDE = auto()
    EXPLORATION = auto()
    COMBAT = auto()
    COLLECTION = auto()

@dataclass
class QuestObjective:
    """Individual quest objective."""
    description: str
    required_progress: int
    current_progress: int = 0
    completed: bool = False
    
    def update_progress(self, amount: int = 1) -> bool:
        """Update objective progress and return True if newly completed."""
        if self.completed:
            return False
            
        self.current_progress = min(
            self.current_progress + amount,
            self.required_progress
        )
        
        if self.current_progress >= self.required_progress:
            self.completed = True
            return True
            
        return False

@dataclass
class QuestReward:
    """Quest reward data."""
    experience: int = 0
    gold: int = 0
    items: List[str] = field(default_factory=list)
    skill_points: int = 0

@dataclass
class Quest:
    """Quest data structure."""
    id: str
    title: str
    description: str
    quest_type: QuestType
    level_requirement: int
    objectives: List[QuestObjective]
    rewards: QuestReward
    status: QuestStatus = QuestStatus.NOT_STARTED
    parent_quest: Optional[str] = None
    child_quests: List[str] = field(default_factory=list)
    on_complete: Optional[Callable[[], None]] = None
    on_fail: Optional[Callable[[], None]] = None
    
    def start(self) -> None:
        """Start the quest."""
        if self.status == QuestStatus.NOT_STARTED:
            self.status = QuestStatus.IN_PROGRESS
            
    def update_objective(self, index: int, amount: int = 1) -> bool:
        """Update an objective's progress and check for quest completion."""
        if self.status != QuestStatus.IN_PROGRESS:
            return False
            
        if 0 <= index < len(self.objectives):
            objective_completed = self.objectives[index].update_progress(amount)
            
            if objective_completed and self.check_completion():
                self.complete()
                return True
                
        return False
        
    def check_completion(self) -> bool:
        """Check if all objectives are completed."""
        return all(obj.completed for obj in self.objectives)
        
    def complete(self) -> None:
        """Complete the quest."""
        if self.status == QuestStatus.IN_PROGRESS:
            self.status = QuestStatus.COMPLETED
            if self.on_complete:
                self.on_complete()
                
    def fail(self) -> None:
        """Fail the quest."""
        if self.status == QuestStatus.IN_PROGRESS:
            self.status = QuestStatus.FAILED
            if self.on_fail:
                self.on_fail()

class QuestManager:
    """Manages quests and their progression."""
    
    def __init__(self):
        self.quests: Dict[str, Quest] = {}
        self.active_quests: Dict[str, Quest] = {}
        self.completed_quests: Dict[str, Quest] = {}
        self.failed_quests: Dict[str, Quest] = {}
        
    def add_quest(self, quest: Quest) -> None:
        """Add a new quest to the system."""
        self.quests[quest.id] = quest
        
    def start_quest(self, quest_id: str) -> bool:
        """Start a quest if requirements are met."""
        if quest_id in self.quests and quest_id not in self.active_quests:
            quest = self.quests[quest_id]
            quest.start()
            self.active_quests[quest_id] = quest
            return True
        return False
        
    def complete_quest(self, quest_id: str) -> None:
        """Complete a quest and process rewards."""
        if quest_id in self.active_quests:
            quest = self.active_quests.pop(quest_id)
            quest.complete()
            self.completed_quests[quest_id] = quest
            
            # Start child quests if any
            for child_id in quest.child_quests:
                self.start_quest(child_id)
                
    def fail_quest(self, quest_id: str) -> None:
        """Fail a quest."""
        if quest_id in self.active_quests:
            quest = self.active_quests.pop(quest_id)
            quest.fail()
            self.failed_quests[quest_id] = quest
            
    def update_quest_progress(self, quest_id: str, objective_index: int,
                            amount: int = 1) -> None:
        """Update progress for a quest objective."""
        if quest_id in self.active_quests:
            self.active_quests[quest_id].update_objective(objective_index, amount)
            
    def get_available_quests(self, player_level: int) -> List[Quest]:
        """Get all available quests for the player's level."""
        return [
            quest for quest in self.quests.values()
            if (quest.status == QuestStatus.NOT_STARTED and
                quest.level_requirement <= player_level and
                (not quest.parent_quest or
                 quest.parent_quest in self.completed_quests))
        ]
        
    def get_quest_chain(self, root_quest_id: str) -> List[Quest]:
        """Get all quests in a quest chain."""
        chain = []
        current_id = root_quest_id
        
        while current_id:
            if current_id in self.quests:
                quest = self.quests[current_id]
                chain.append(quest)
                current_id = quest.child_quests[0] if quest.child_quests else None
                
        return chain

def create_main_quest_line() -> List[Quest]:
    """Create the main quest line for the game."""
    quests = []
    
    # First quest: Awakening
    awakening = Quest(
        id="main_01_awakening",
        title="Awakening",
        description="Discover your purpose in the infinite megastructure.",
        quest_type=QuestType.MAIN,
        level_requirement=1,
        objectives=[
            QuestObjective("Explore the starting sector", 1),
            QuestObjective("Find the ancient terminal", 1),
            QuestObjective("Access the terminal's memory banks", 1)
        ],
        rewards=QuestReward(
            experience=1000,
            gold=100,
            items=["ancient_data_crystal"],
            skill_points=1
        )
    )
    quests.append(awakening)
    
    # Second quest: The Path Forward
    path_forward = Quest(
        id="main_02_path_forward",
        title="The Path Forward",
        description="Begin your journey through the megastructure.",
        quest_type=QuestType.MAIN,
        level_requirement=2,
        objectives=[
            QuestObjective("Find the sector gateway", 1),
            QuestObjective("Defeat the guardian construct", 1),
            QuestObjective("Activate the gateway", 1)
        ],
        rewards=QuestReward(
            experience=2000,
            gold=200,
            items=["gateway_key"],
            skill_points=2
        ),
        parent_quest="main_01_awakening"
    )
    awakening.child_quests.append(path_forward.id)
    quests.append(path_forward)
    
    # Third quest: The Hidden Truth
    hidden_truth = Quest(
        id="main_03_hidden_truth",
        title="The Hidden Truth",
        description="Uncover the secrets of the megastructure's creation.",
        quest_type=QuestType.MAIN,
        level_requirement=4,
        objectives=[
            QuestObjective("Locate the ancient archives", 1),
            QuestObjective("Collect memory fragments", 5),
            QuestObjective("Decrypt the ancient logs", 1)
        ],
        rewards=QuestReward(
            experience=4000,
            gold=400,
            items=["architect_cipher", "ancient_blueprint"],
            skill_points=3
        ),
        parent_quest="main_02_path_forward"
    )
    path_forward.child_quests.append(hidden_truth.id)
    quests.append(hidden_truth)
    
    return quests
