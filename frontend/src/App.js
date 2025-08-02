import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Bell, MessageSquare, BookOpen, Users, PlusCircle, LogIn, Presentation, FileText, Video, Mic, Send } from 'lucide-react';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [classes, setClasses] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [messages, setMessages] = useState([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleSlides, setGoogleSlides] = useState([]);
  const [googleDocs, setGoogleDocs] = useState([]);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    const sessionId = getCookie('session_id');
    if (sessionId) {
      try {
        const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
          headers: {
            'X-Session-ID': sessionId
          }
        });
        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
          await loadDashboardData(sessionId);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
      }
    }
    setLoading(false);
  };

  const loadDashboardData = async (sessionId) => {
    try {
      const headers = { 'X-Session-ID': sessionId };
      
      const [classesRes, lessonsRes, notificationsRes, messagesRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/classes`, { headers }),
        fetch(`${BACKEND_URL}/api/lessons`, { headers }),
        fetch(`${BACKEND_URL}/api/notifications`, { headers }),
        fetch(`${BACKEND_URL}/api/messages`, { headers })
      ]);

      if (classesRes.ok) setClasses(await classesRes.json());
      if (lessonsRes.ok) setLessons(await lessonsRes.json());
      if (notificationsRes.ok) setNotifications(await notificationsRes.json());
      if (messagesRes.ok) setMessages(await messagesRes.json());
      
      // Try to load Google data (will fail silently if not connected)
      loadGoogleData();
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  };

  const handleLogin = () => {
    const currentUrl = window.location.origin;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(currentUrl)}`;
  };

  const handleAuthCallback = async () => {
    const hash = window.location.hash;
    if (hash && hash.includes('session_id=')) {
      const sessionId = hash.split('session_id=')[1];
      
      try {
        const response = await fetch(`${BACKEND_URL}/api/auth/profile`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ session_id: sessionId })
        });

        if (response.ok) {
          const data = await response.json();
          setCookie('session_id', sessionId, 7);
          window.location.hash = '';
          checkAuthStatus();
        }
      } catch (error) {
        console.error('Authentication failed:', error);
      }
    }
  };

  const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  };

  const setCookie = (name, value, days) => {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${name}=${value}; expires=${expires}; path=/`;
  };

  const handleLogout = () => {
    document.cookie = 'session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    setUser(null);
    setClasses([]);
    setLessons([]);
    setNotifications([]);
    setMessages([]);
  };

  const createClass = async (classData) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/classes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify(classData)
      });

      if (response.ok) {
        const newClass = await response.json();
        setClasses([...classes, newClass]);
        return newClass;
      }
    } catch (error) {
      console.error('Failed to create class:', error);
    }
  };

  const createLesson = async (lessonData) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/lessons`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify(lessonData)
      });

      if (response.ok) {
        const newLesson = await response.json();
        setLessons([newLesson, ...lessons]);
        return newLesson;
      }
    } catch (error) {
      console.error('Failed to create lesson:', error);
    }
  };

  const connectGoogle = async () => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/google/auth-url`, {
        headers: { 'X-Session-ID': sessionId }
      });
      
      if (response.ok) {
        const data = await response.json();
        window.open(data.auth_url, '_blank', 'width=500,height=600');
      }
    } catch (error) {
      console.error('Failed to get Google auth URL:', error);
    }
  };

  const loadGoogleData = async () => {
    const sessionId = getCookie('session_id');
    try {
      const headers = { 'X-Session-ID': sessionId };
      
      const [slidesRes, docsRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/google/slides`, { headers }),
        fetch(`${BACKEND_URL}/api/google/docs`, { headers })
      ]);

      if (slidesRes.ok) {
        const slidesData = await slidesRes.json();
        setGoogleSlides(slidesData.presentations);
        setGoogleConnected(true);
      }
      
      if (docsRes.ok) {
        const docsData = await docsRes.json();
        setGoogleDocs(docsData.documents);
      }
    } catch (error) {
      console.error('Failed to load Google data:', error);
    }
  };

  const importSlides = async (slidesId, lessonId = null) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/google/import-slides`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({ slides_id: slidesId, lesson_id: lessonId })
      });

      if (response.ok) {
        const result = await response.json();
        alert('Slides imported successfully!');
        return result;
      }
    } catch (error) {
      console.error('Failed to import slides:', error);
    }
  };

  const importDocs = async (docsId, lessonId = null) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/google/import-docs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({ docs_id: docsId, lesson_id: lessonId })
      });

      if (response.ok) {
        const result = await response.json();
        alert('Document imported successfully!');
        return result;
      }
    } catch (error) {
      console.error('Failed to import document:', error);
    }
  };

  const sendMessage = async (messageData) => {
    const sessionId = getCookie('session_id');
    try {
      const response = await fetch(`${BACKEND_URL}/api/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify(messageData)
      });

      if (response.ok) {
        const newMessage = await response.json();
        setMessages([newMessage, ...messages]);
        return newMessage;
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  useEffect(() => {
    handleAuthCallback();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-midnight-900 via-black to-midnight-800 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gold-400"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-midnight-900 via-black to-midnight-800 flex items-center justify-center">
        <div className="max-w-md w-full space-y-8 p-8">
          <div className="text-center">
            <BookOpen className="mx-auto h-16 w-16 text-gold-400 mb-6" />
            <h2 className="text-4xl font-bold text-white mb-2">LessonHub</h2>
            <p className="text-gray-300 mb-8">Your comprehensive classroom management platform</p>
            <Button 
              onClick={handleLogin}
              className="w-full bg-gold-600 hover:bg-gold-700 text-black font-semibold py-3 px-6 rounded-xl transition-all duration-300 transform hover:scale-105"
            >
              <LogIn className="mr-2 h-5 w-5" />
              Sign in with Google
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-midnight-900 via-black to-midnight-800">
      {/* Header */}
      <header className="bg-black/50 backdrop-blur-lg border-b border-midnight-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <BookOpen className="h-8 w-8 text-gold-400" />
              <h1 className="text-2xl font-bold text-white">LessonHub</h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="relative">
                <Bell className="h-6 w-6 text-gray-300 hover:text-gold-400 cursor-pointer transition-colors" />
                {notifications.filter(n => !n.read).length > 0 && (
                  <Badge className="absolute -top-2 -right-2 bg-gold-600 text-black text-xs">
                    {notifications.filter(n => !n.read).length}
                  </Badge>
                )}
              </div>
              
              <div className="flex items-center space-x-3">
                <img 
                  src={user.picture} 
                  alt={user.name}
                  className="h-8 w-8 rounded-full border-2 border-gold-400"
                />
                <span className="text-white font-medium">{user.name}</span>
                <Button 
                  variant="ghost" 
                  onClick={handleLogout}
                  className="text-gray-300 hover:text-white hover:bg-midnight-800"
                >
                  Logout
                </Button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-5 mb-8 bg-midnight-800/50 backdrop-blur-lg border border-midnight-700">
            <TabsTrigger value="dashboard" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Dashboard
            </TabsTrigger>
            <TabsTrigger value="classes" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Classes
            </TabsTrigger>
            <TabsTrigger value="lessons" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Lessons
            </TabsTrigger>
            <TabsTrigger value="google" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Google Import
            </TabsTrigger>
            <TabsTrigger value="messages" className="data-[state=active]:bg-gold-600 data-[state=active]:text-black">
              Messages
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatsCard
                title="Classes"
                value={classes.length}
                icon={<Users className="h-8 w-8 text-gold-400" />}
                description="Active classrooms"
              />
              <StatsCard
                title="Lessons"
                value={lessons.length}
                icon={<BookOpen className="h-8 w-8 text-gold-400" />}
                description="Total lessons created"
              />
              <StatsCard
                title="Messages"
                value={messages.length}
                icon={<MessageSquare className="h-8 w-8 text-gold-400" />}
                description="Recent conversations"
              />
              <StatsCard
                title="Notifications"
                value={notifications.filter(n => !n.read).length}
                icon={<Bell className="h-8 w-8 text-gold-400" />}
                description="Unread notifications"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <RecentLessons lessons={lessons.slice(0, 5)} />
              <RecentNotifications notifications={notifications.slice(0, 5)} />
            </div>
          </TabsContent>

          {/* Classes Tab */}
          <TabsContent value="classes" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">My Classes</h2>
              {user.role === 'teacher' && <CreateClassDialog onCreateClass={createClass} />}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {classes.map(classItem => (
                <ClassCard key={classItem.id} classData={classItem} />
              ))}
            </div>
          </TabsContent>

          {/* Lessons Tab */}
          <TabsContent value="lessons" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">Lessons</h2>
              {user.role === 'teacher' && <CreateLessonDialog classes={classes} onCreateLesson={createLesson} />}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {lessons.map(lesson => (
                <LessonCard key={lesson.id} lesson={lesson} />
              ))}
            </div>
          </TabsContent>

          {/* Google Import Tab */}
          <TabsContent value="google" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">Google Import</h2>
              {!googleConnected && (
                <Button onClick={connectGoogle} className="bg-gold-600 hover:bg-gold-700 text-black">
                  <LogIn className="mr-2 h-4 w-4" />
                  Connect Google Account
                </Button>
              )}
            </div>
            
            {googleConnected ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Google Slides */}
                <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center">
                      <Presentation className="mr-2 h-5 w-5 text-gold-400" />
                      Google Slides
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      Import your presentations into lessons
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Button onClick={loadGoogleData} className="mb-4 bg-midnight-700 hover:bg-midnight-600 text-white">
                      Refresh Lists
                    </Button>
                    {googleSlides.map(slide => (
                      <div key={slide.id} className="flex items-center justify-between p-3 rounded-lg bg-black/30 hover:bg-black/50 transition-colors">
                        <div className="flex-1">
                          <h4 className="font-medium text-white">{slide.name}</h4>
                          <p className="text-sm text-gray-400">
                            Modified: {new Date(slide.modifiedTime).toLocaleDateString()}
                          </p>
                        </div>
                        <Button 
                          onClick={() => importSlides(slide.id)}
                          className="bg-gold-600 hover:bg-gold-700 text-black text-sm"
                        >
                          Import
                        </Button>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                {/* Google Docs */}
                <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center">
                      <FileText className="mr-2 h-5 w-5 text-gold-400" />
                      Google Docs
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      Import your documents as lesson plans
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {googleDocs.map(doc => (
                      <div key={doc.id} className="flex items-center justify-between p-3 rounded-lg bg-black/30 hover:bg-black/50 transition-colors">
                        <div className="flex-1">
                          <h4 className="font-medium text-white">{doc.name}</h4>
                          <p className="text-sm text-gray-400">
                            Modified: {new Date(doc.modifiedTime).toLocaleDateString()}
                          </p>
                        </div>
                        <Button 
                          onClick={() => importDocs(doc.id)}
                          className="bg-gold-600 hover:bg-gold-700 text-black text-sm"
                        >
                          Import
                        </Button>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            ) : (
              <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
                <CardContent className="p-8 text-center">
                  <Presentation className="mx-auto h-16 w-16 text-gold-400 mb-4" />
                  <h3 className="text-xl font-semibold text-white mb-2">Connect Your Google Account</h3>
                  <p className="text-gray-400 mb-6">
                    Connect your Google account to import slides and documents directly into your lessons.
                  </p>
                  <Button onClick={connectGoogle} className="bg-gold-600 hover:bg-gold-700 text-black">
                    <LogIn className="mr-2 h-4 w-4" />
                    Connect Google Account
                  </Button>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Messages Tab */}
          <TabsContent value="messages" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">Messages</h2>
              <MessageDialog onSendMessage={sendMessage} />
            </div>
            
            <div className="space-y-4">
              {messages.map(message => (
                <MessageCard key={message.id} message={message} currentUser={user} />
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

// Component definitions
const StatsCard = ({ title, value, icon, description }) => (
  <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700 hover:border-gold-400/50 transition-all duration-300">
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium text-gray-300">{title}</CardTitle>
      {icon}
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold text-white">{value}</div>
      <p className="text-xs text-gray-400">{description}</p>
    </CardContent>
  </Card>
);

const RecentLessons = ({ lessons }) => (
  <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
    <CardHeader>
      <CardTitle className="text-white">Recent Lessons</CardTitle>
    </CardHeader>
    <CardContent className="space-y-4">
      {lessons.map(lesson => (
        <div key={lesson.id} className="flex items-center space-x-4 p-3 rounded-lg bg-black/30 hover:bg-black/50 transition-colors">
          <BookOpen className="h-8 w-8 text-gold-400" />
          <div className="flex-1">
            <h4 className="font-medium text-white">{lesson.title}</h4>
            <p className="text-sm text-gray-400">{lesson.description}</p>
          </div>
        </div>
      ))}
    </CardContent>
  </Card>
);

const RecentNotifications = ({ notifications }) => (
  <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700">
    <CardHeader>
      <CardTitle className="text-white">Recent Notifications</CardTitle>
    </CardHeader>
    <CardContent className="space-y-4">
      {notifications.map(notification => (
        <div key={notification.id} className="flex items-center space-x-4 p-3 rounded-lg bg-black/30 hover:bg-black/50 transition-colors">
          <Bell className="h-6 w-6 text-gold-400" />
          <div className="flex-1">
            <h4 className="font-medium text-white">{notification.title}</h4>
            <p className="text-sm text-gray-400">{notification.message}</p>
          </div>
          {!notification.read && <div className="w-2 h-2 bg-gold-400 rounded-full"></div>}
        </div>
      ))}
    </CardContent>
  </Card>
);

const ClassCard = ({ classData }) => (
  <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700 hover:border-gold-400/50 transition-all duration-300 hover:scale-105">
    <CardHeader>
      <CardTitle className="text-white">{classData.name}</CardTitle>
      <CardDescription className="text-gray-400">{classData.description}</CardDescription>
    </CardHeader>
    <CardContent>
      <div className="flex items-center justify-between">
        <Badge className="bg-gold-600/20 text-gold-400 border-gold-400/30">
          {classData.students.length} Students
        </Badge>
        <Users className="h-5 w-5 text-gray-400" />
      </div>
    </CardContent>
  </Card>
);

const LessonCard = ({ lesson }) => (
  <Card className="bg-midnight-800/50 backdrop-blur-lg border-midnight-700 hover:border-gold-400/50 transition-all duration-300 hover:scale-105">
    <CardHeader>
      <CardTitle className="text-white">{lesson.title}</CardTitle>
      <CardDescription className="text-gray-400">{lesson.description}</CardDescription>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="flex items-center space-x-2">
        {lesson.google_slides_id && <Presentation className="h-4 w-4 text-gold-400" />}
        {lesson.google_docs_id && <FileText className="h-4 w-4 text-gold-400" />}
        {lesson.video_url && <Video className="h-4 w-4 text-gold-400" />}
        {lesson.audio_url && <Mic className="h-4 w-4 text-gold-400" />}
      </div>
      <Badge className="bg-midnight-700 text-gray-300">
        {new Date(lesson.created_at).toLocaleDateString()}
      </Badge>
    </CardContent>
  </Card>
);

const MessageCard = ({ message, currentUser }) => (
  <Card className={`bg-midnight-800/50 backdrop-blur-lg border-midnight-700 ${
    message.sender_id === currentUser.id ? 'ml-auto max-w-md' : 'mr-auto max-w-md'
  }`}>
    <CardContent className="p-4">
      <div className="flex items-start space-x-3">
        <div className="flex-1">
          <p className="text-white">{message.message}</p>
          <p className="text-xs text-gray-400 mt-2">
            {new Date(message.created_at).toLocaleString()}
          </p>
        </div>
      </div>
    </CardContent>
  </Card>
);

const CreateClassDialog = ({ onCreateClass }) => {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    await onCreateClass({ name, description });
    setName('');
    setDescription('');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-gold-600 hover:bg-gold-700 text-black">
          <PlusCircle className="mr-2 h-4 w-4" />
          Create Class
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-midnight-800 border-midnight-700">
        <DialogHeader>
          <DialogTitle className="text-white">Create New Class</DialogTitle>
          <DialogDescription className="text-gray-400">
            Create a new classroom to organize your lessons and students.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Class Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
            required
          />
          <Textarea
            placeholder="Class Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
          />
          <Button type="submit" className="w-full bg-gold-600 hover:bg-gold-700 text-black">
            Create Class
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

const CreateLessonDialog = ({ classes, onCreateLesson }) => {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [classId, setClassId] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    await onCreateLesson({ title, description, class_id: classId });
    setTitle('');
    setDescription('');
    setClassId('');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-gold-600 hover:bg-gold-700 text-black">
          <PlusCircle className="mr-2 h-4 w-4" />
          Create Lesson
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-midnight-800 border-midnight-700">
        <DialogHeader>
          <DialogTitle className="text-white">Create New Lesson</DialogTitle>
          <DialogDescription className="text-gray-400">
            Create a new lesson with Google Slides and Docs integration.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Lesson Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
            required
          />
          <Textarea
            placeholder="Lesson Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
          />
          <select
            value={classId}
            onChange={(e) => setClassId(e.target.value)}
            className="w-full p-2 rounded-md bg-midnight-900 border border-midnight-600 text-white"
            required
          >
            <option value="">Select Class</option>
            {classes.map(classItem => (
              <option key={classItem.id} value={classItem.id}>
                {classItem.name}
              </option>
            ))}
          </select>
          <Button type="submit" className="w-full bg-gold-600 hover:bg-gold-700 text-black">
            Create Lesson
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

const MessageDialog = ({ onSendMessage }) => {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [recipientId, setRecipientId] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    await onSendMessage({ message, recipient_id: recipientId });
    setMessage('');
    setRecipientId('');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-gold-600 hover:bg-gold-700 text-black">
          <Send className="mr-2 h-4 w-4" />
          New Message
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-midnight-800 border-midnight-700">
        <DialogHeader>
          <DialogTitle className="text-white">Send Message</DialogTitle>
          <DialogDescription className="text-gray-400">
            Send a message to students or other teachers.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Recipient ID"
            value={recipientId}
            onChange={(e) => setRecipientId(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
            required
          />
          <Textarea
            placeholder="Your message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="bg-midnight-900 border-midnight-600 text-white"
            required
          />
          <Button type="submit" className="w-full bg-gold-600 hover:bg-gold-700 text-black">
            Send Message
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default App;