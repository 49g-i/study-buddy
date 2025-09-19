'use client';

import TextType from '@/components/TextType/TextType';

export default function Hero() {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-900 text-white">
      <h1 className="text-4xl font-bold mb-4">Welcome to StudyBuddy 🚀</h1>

      <TextType
        text={[
          "Find your perfect study partner",
          "Chat in real-time",
          "Track who's online",
          "Never miss a message"
        ]}
        as="h2"
        typingSpeed={80}
        deletingSpeed={40}
        pauseDuration={1500}
        loop={true}
        showCursor={true}
        hideCursorWhileTyping={false}
        cursorCharacter="|"
        cursorBlinkDuration={0.4}
        textColors={["#ff4d6d", "#4dff91", "#4da6ff"]}
        variableSpeed={{ min: 40, max: 120 }}
        className="text-2xl"
        onSentenceComplete={(text, index) =>
          console.log(`Completed sentence: ${text} (index: ${index})`)
        }
      />
    </div>
  );
}
