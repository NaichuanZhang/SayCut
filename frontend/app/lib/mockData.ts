import { Scene } from "./types";

export const MOCK_SCENES: readonly Scene[] = [
  {
    id: "scene-1",
    index: 0,
    title: "The Whispering Forest",
    narrationText:
      "Deep in the emerald heart of the ancient forest, where sunlight filtered through a cathedral of leaves, a tiny fox named Ember discovered a glowing acorn pulsing with golden light.",
    visualDescription:
      "A small red fox sitting in a lush green forest clearing, golden light filtering through tall trees, a glowing golden acorn on the ground, magical atmosphere, cinematic lighting",
    imageUrl: "https://picsum.photos/seed/scene1/800/450",
    videoUrl: null,
    audioUrl: null,
    status: "ready",
  },
  {
    id: "scene-2",
    index: 1,
    title: "The River of Stars",
    narrationText:
      "Ember carried the acorn to the river that flowed through the valley. But this was no ordinary river — at night, it reflected not the sky above, but a sky from another world entirely.",
    visualDescription:
      "A fox walking along a riverbank at twilight, the river reflecting an alien starscape with nebulae and two moons, bioluminescent plants along the shore",
    imageUrl: "https://picsum.photos/seed/scene2/800/450",
    videoUrl: null,
    audioUrl: null,
    status: "ready",
  },
  {
    id: "scene-3",
    index: 2,
    title: "The Guardian's Riddle",
    narrationText:
      "At the river's bend stood a great stone owl, its eyes made of moonstone. 'To unlock the acorn's gift,' it spoke in a voice like wind through chimes, 'you must answer what is always coming but never arrives.'",
    visualDescription:
      "A massive stone owl statue covered in moss and vines, moonstone glowing eyes, a tiny fox looking up at it, misty forest background, dramatic lighting",
    imageUrl: "https://picsum.photos/seed/scene3/800/450",
    videoUrl: null,
    audioUrl: null,
    status: "ready",
  },
  {
    id: "scene-4",
    index: 3,
    title: "Tomorrow's Light",
    narrationText:
      "Ember thought for a long moment, then smiled. 'Tomorrow,' she whispered. The acorn cracked open, releasing a swirl of golden butterflies that carried the forest's magic into every corner of the land.",
    visualDescription:
      "A fox surrounded by hundreds of glowing golden butterflies erupting from a cracked acorn, magical particles in the air, forest bathed in warm golden light, triumphant cinematic moment",
    imageUrl: "https://picsum.photos/seed/scene4/800/450",
    videoUrl: null,
    audioUrl: null,
    status: "ready",
  },
];

export const MOCK_AGENT_RESPONSES = {
  welcome:
    "Hi! I'm your storybook creator. Hold the orb and tell me about a story you'd like to make.",
  firstInteraction:
    "That sounds wonderful! Let me create a storybook for you. I'll start by writing a script with scenes, then generate images for each one.",
  scriptReady:
    "I've created a 4-scene storybook called \"The Whispering Forest\" — a magical tale about a brave little fox named Ember. Let me generate the visuals for each scene now.",
  sceneImageDone: (index: number) =>
    `Scene ${index + 1} image is ready! Take a look at the storyboard above.`,
  followUp:
    "Your storybook is taking shape! You can tap any scene card to see it in detail, or hold the orb to tell me about any changes you'd like.",
  genericResponses: [
    "I love that idea! Let me think about how to incorporate that into the story.",
    "Great suggestion. I can adjust the scene to match your vision.",
    "That's a creative direction! The storybook is really coming together.",
    "Interesting! I'll keep that in mind as we refine the scenes.",
  ],
} as const;
