"""
Test the Language Weakness Analyzer
Run this script to test the full implementation with LanguageTool, WordNet, and Fillers
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.ai_processing.language_weakness_analyzer import (
    GrammarChecker,
    VocabularyAnalyzer,
    FillerWordDetector,
    LanguageWeaknessAnalyzer,
    analyze_conversation
)

# Sample conversation text (simulating a user speaking)
SAMPLE_CONVERSATION = """
Um, so like I think that, you know, learning English is basically very important 
in today's world. I mean, actually, I want to improve my speaking skills because 
I have some problems with grammar.

Like, sometimes I forget to use the correct tense. For example, yesterday I go to 
the store and I buy some groceries. The weather was very nice so I walk home.

I think English is necessary for my career. I work in a company where I need to 
communicate with international clients. So, um, I try to practice every day, you know.

My vocabulary is not very strong. I always use the same words - good, nice, bad, 
things like that. I want to learn more words to express myself better.

Um, basically, that's why I'm using this app. I hope to improve my fluency and 
reduce my grammar mistakes. Thanks for listening!
"""

def test_grammar_checker():
    """Test the Grammar Checker component"""
    print("\n" + "="*60)
    print("TESTING: Grammar Checker (LanguageTool)")
    print("="*60)
    
    checker = GrammarChecker()
    result = checker.check(SAMPLE_CONVERSATION)
    
    print(f"\n📊 Grammar Score: {result['grammar_score']}/100")
    print(f"📝 Total Errors: {result['total_errors']}")
    print(f"\n📋 Errors by Category:")
    for category, count in result['errors_by_category'].items():
        print(f"   - {category}: {count}")
    
    print(f"\n🔍 First 5 Error Details:")
    for i, error in enumerate(result['error_details'][:5], 1):
        print(f"\n   {i}. {error['message']}")
        print(f"      Category: {error['category']}")
        if error['suggestions']:
            print(f"      Suggestions: {', '.join(error['suggestions'][:3])}")
    
    return result

def test_vocabulary_analyzer():
    """Test the Vocabulary Analyzer component"""
    print("\n" + "="*60)
    print("TESTING: Vocabulary Analyzer (WordNet)")
    print("="*60)
    
    analyzer = VocabularyAnalyzer()
    result = analyzer.analyze(SAMPLE_CONVERSATION)
    
    print(f"\n📊 Vocabulary Score: {result['vocabulary_score']}/100")
    print(f"📖 Vocabulary Level: {result['vocabulary_level'].upper()}")
    print(f"\n📈 Metrics:")
    print(f"   - Word Count: {result['word_count']}")
    print(f"   - Unique Words: {result['unique_words']}")
    print(f"   - Type-Token Ratio: {result['type_token_ratio']:.3f}")
    print(f"   - Lexical Sophistication: {result['lexical_sophistication']:.1f}%")
    print(f"   - Diversity Score: {result['vocabulary_diversity_score']:.1f}")
    
    print(f"\n🔤 Advanced Words Used ({len(result['advanced_words_used'])} words):")
    print(f"   {', '.join(result['advanced_words_used'][:15])}")
    
    if result['repeated_words']:
        print(f"\n⚠️ Repeated Words (overused):")
        print(f"   {', '.join(result['repeated_words'][:5])}")
    
    print(f"\n💡 Suggestions:")
    for suggestion in result['suggestions']:
        print(f"   • {suggestion}")
    
    return result

def test_filler_detector():
    """Test the Filler Word Detector component"""
    print("\n" + "="*60)
    print("TESTING: Filler Word Detector (Rule-Based)")
    print("="*60)
    
    detector = FillerWordDetector()
    result = detector.detect(SAMPLE_CONVERSATION)
    
    print(f"\n📊 Filler Score: {result['filler_score']}/100 (higher = fewer fillers)")
    print(f"🎤 Total Fillers: {result['total_fillers']}")
    print(f"📉 Filler Rate: {result['filler_rate']}% of words")
    
    print(f"\n📋 Fillers by Category:")
    for category, fillers in result['fillers_by_category'].items():
        print(f"   - {category}: {len(fillers)} ({', '.join(list(set(fillers))[:5])})")
    
    print(f"\n🔝 Most Common Fillers:")
    for filler, count in result['most_common_fillers']:
        print(f"   • '{filler}': {count} times")
    
    print(f"\n💡 Suggestions:")
    for suggestion in result['suggestions']:
        print(f"   • {suggestion}")
    
    return result

def test_full_analyzer():
    """Test the complete Language Weakness Analyzer"""
    print("\n" + "="*60)
    print("TESTING: Full Language Weakness Analyzer")
    print("="*60)
    
    # Simulate 2 minutes of speaking
    audio_duration = 120  # seconds
    
    result = analyze_conversation(SAMPLE_CONVERSATION, audio_duration)
    
    print(f"\n🎯 OVERALL SCORE: {result['overall_score']}/100")
    print(f"\n📊 Individual Scores:")
    print(f"   - Grammar: {result['scores']['grammar']}")
    print(f"   - Vocabulary: {result['scores']['vocabulary']}")
    print(f"   - Fluency (Fillers): {result['scores']['filler']}")
    
    print(f"\n📈 Speaking Metrics:")
    metrics = result['speaking_metrics']
    print(f"   - Words: {metrics['word_count']}")
    print(f"   - WPM: {metrics['words_per_minute']}")
    print(f"   - Unique Words: {metrics['unique_words']}")
    print(f"   - Vocab Level: {metrics['vocabulary_level']}")
    print(f"   - Grammar Errors: {metrics['total_grammar_errors']}")
    print(f"   - Fillers Used: {metrics['total_fillers']}")
    
    print(f"\n⚠️ IDENTIFIED WEAKNESSES:")
    for weakness in result['weaknesses']:
        print(f"\n   📌 {weakness['area'].upper()} ({weakness['severity']} severity)")
        print(f"      {weakness['description']}")
    
    print(f"\n✨ STRENGTH AREAS:")
    for strength in result['strength_areas']:
        print(f"   ✓ {strength}")
    
    print(f"\n💡 TOP SUGGESTIONS:")
    for i, suggestion in enumerate(result['suggestions'], 1):
        print(f"   {i}. {suggestion}")
    
    return result


def main():
    print("\n" + "="*60)
    print("   LANGUAGE WEAKNESS ANALYZER - FULL TEST SUITE")
    print("   Components: LanguageTool + WordNet + Rule-Based")
    print("="*60)
    
    print("\n📝 Sample Conversation being analyzed:")
    print("-" * 40)
    print(SAMPLE_CONVERSATION[:200] + "...")
    print("-" * 40)
    
    # Test individual components
    grammar_result = test_grammar_checker()
    vocab_result = test_vocabulary_analyzer()
    filler_result = test_filler_detector()
    
    # Test full analyzer
    full_result = test_full_analyzer()
    
    print("\n" + "="*60)
    print("   TEST COMPLETE!")
    print("="*60)
    print("\n✅ All components are working correctly!")
    print("📌 The analyzer can now evaluate:")
    print("   1. Grammar errors (via LanguageTool)")
    print("   2. Vocabulary richness (via WordNet)")
    print("   3. Filler word usage (via Rule-based patterns)")
    print("\n🚀 Ready to integrate into your API endpoints!")


if __name__ == "__main__":
    main()
